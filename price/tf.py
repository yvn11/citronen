#
#
import os
import sys
import glob
import pandas as pd
import numpy as np
#import seaborn as sns
#from matplotlib import pyplot as plt
from sklearn import preprocessing
from sklearn.feature_extraction.text import TfidfVectorizer
import tensorflow as tf
from sklearn.utils import shuffle
import pickle


BATCH_SIZE = 64
path = 'data/price/train.tsv'

def preprocess(need_shuffle=True):
    global path
    batch_size = BATCH_SIZE
    gen = pd.read_csv(path, delimiter='\t', chunksize=batch_size)
    yield from [foreach_df(df, need_shuffle) for df in gen]


def foreach_df(df, need_shuffle=True):
    df = df.drop_duplicates()
    if need_shuffle:
        df = shuffle(df)

    X = encode_text(df)
    X = np.concatenate((X, df['shipping'].values.reshape(X.shape[0], 1)), 1).astype(np.float)
    target = df['price'].astype(np.float)
    X = X.reshape(X.shape[0], X.shape[1], 1)
    y = target.values.reshape(target.shape[0], 1)
    return X, y

def encode_text(df):
    path = 'data/price/content.pickle'

    cate = df['category_name'].fillna('').values
    name = df['name'].fillna('').values
    desc = df['item_description'].fillna('').values
    
    content = list(map(lambda l: ' '.join([l[0], l[1]]), zip(cate, name)))
    content = list(map(lambda l: ' '.join([l[0], l[1]]), zip(content, desc)))
    le, ret = load_or_fit(path, content=content)
    return ret

def encode_cate(df):
    path = 'data/price/cate.pickle'
    le, cate = load_or_fit(df, path, 'category_name')
    return cate
        
def encode_name(df):
    path = 'data/price/name.pickle'
    le, name = load_or_fit(df, path, 'name')
    return name

def encode_desc(df):
    path = 'data/price/desc.pickle'
    le, desc = load_or_fit(df, path, 'item_description')
    return desc


def load_or_fit(path, df=None, field=None, content=None):
    if field and df:
        input_x = df[field].fillna('')

    if content:
        input_x = content

    if not os.path.isfile(path):
        le = TfidfVectorizer()
        le = le.fit(input_x)

        with open(path, 'wb') as fd:
            pickle.dump(le, fd)
    else:
        with open(path, 'rb') as fd:
            le = pickle.load(fd)
    
    ret = le.transform(input_x).toarray()
    return le, ret#.reshape(ret.shape[0], ret.shape[1])


class Price(object):

    def __init__(self):
        super(Price, self).__init__()
        self.epochs = 1000000
        self.lr = 1e-3
        self.init_step = 0
        self.dropout_rate = 0.4
        self.summ_intv = 1000
        self.model_dir = "models/price"
        self.log_path = os.path.join(self.model_dir, 'cnn')
        self.total_feat = 942
        self.channel = 1

    def _build_model(self):
        with tf.device('/cpu:0'):
            self.input_x = tf.placeholder(tf.float32, (None, self.total_feat, self.channel), name='input_x')
            self.input_y = tf.placeholder(tf.float32, (None, 1), name='input_y')
            self.dropout_keep = tf.placeholder(tf.float32, name='dropout_keep')

        self.layers = []
        total_layers = 5

        with tf.device('/cpu:0'):
            for i in range(total_layers):
                if not self.layers:
                    conv = tf.layers.conv1d(self.input_x, 3, kernel_size=5, name='conv_{}'.format(i))
                else:
                    conv = tf.layers.conv1d(self.layers[-1], 3, kernel_size=5, name='conv_{}'.format(i))
                pool = tf.layers.max_pooling1d(conv, [3], [1], name='pool_{}'.format(i))
                self.layers.append(pool)

        print(self.layers)

        flat = tf.reshape(self.layers[-1], [-1, 2736*64])
        hidden = tf.nn.dropout(flat, self.dropout_keep)

        with tf.device('/cpu:0'):
            self.logits = tf.layers.dense(hidden, 1, use_bias=True,
                kernel_initializer=tf.contrib.layers.xavier_initializer(), name='logits')

        print('logits', self.logits)
        self.loss = tf.reduce_mean(tf.pow(tf.log(self.logits+1)-tf.log(self.input_y+1), 2), name='loss')
        #self.loss = tf.losses.log_loss(self.input_y, self.logits)
        self.global_step = tf.Variable(self.init_step, name="global_step", trainable=False)
        self.train_op = tf.train.RMSPropOptimizer(self.lr, momentum=0.9).minimize(\
            self.loss, global_step=self.global_step, name='train_op')

        summary = []
        summary.append(tf.summary.scalar('loss', self.loss))
        summary.append(tf.summary.histogram('logits', self.logits))
        summary.extend([tf.summary.histogram('pool_{}'.format(i), pool) for i, pool in enumerate(self.layers)])
        self.summary = tf.summary.merge(summary, name='summary')

    def train(self):
        self._build_model()
        #self.estimator.train(input_fn=preprocess, steps=100)
        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            self.summary_writer = tf.summary.FileWriter(self.log_path, sess.graph)
            self.saver = tf.train.Saver(tf.global_variables())

            for e in range(self.epochs):
                self.foreach_epoch(sess, e)
     
    def foreach_epoch(self, sess, e):
        for X, y in preprocess():
            feed_dict = {
                self.input_x: X,
                self.input_y: y,
                self.dropout_keep: 1-self.dropout_rate,
                }

            _, loss, pred, step, summ = sess.run(\
                [self.train_op, self.loss, self.logits, self.global_step, self.summary],\
                feed_dict=feed_dict)
            pred = np.squeeze(pred)

            if step % self.summ_intv == 0:
                print('++ [step-{}] loss:{} pred:{}'.format(step, loss, pred))
                self.summary_writer.add_summary(summ, step)
                self.saver.save(sess, self.model_dir+'/cnn',
                            global_step=tf.train.global_step(sess, self.global_step))
                self.inner_test(sess, step)
    

    def inner_test(self, sess, step):
        global path

        def foreach_chunk(iid, X):
    
            feed_dict = {
               self.input_x: X,
               self.dropout_keep: 1,
               }
    
            pred = sess.run([self.logits], feed_dict=feed_dict)    
            pred = np.squeeze(pred)

            print('++ [inference] {}'.format(pred))
            df = pd.DataFrame({
                    'test_id': iid,
                    'price': pred,
                })

            if not os.path.isfile(result_path):
                df.to_csv(result_path, index=None, float_format='%0.6f')
            else:
                df.to_csv(result_path, index=None, float_format='%0.6f', header=False, mode='a')

        prev_path = path
        path = "data/price/test.tsv"
        result_path = "data/price/pred_tf_{}_{}.csv".format(\
                    step,
                    datetime.now().strftime("%y%m%d%H%M"))
    
        gen = preprocess(need_shuffle=False)
        [foreach_chunk(iid, X) for iid, X in gen]
        path = prev_path


def start():
    #for x, y in preprocess():
    #    print(x.shape)
    obj = Price()
    obj.train()

if __name__ == '__main__':
    start()
    #for x, y in preprocess():
    #    print(x.shape, y.shape)
