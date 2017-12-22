#!/bin/bash
ETL_ROOT=/opt/360-etl
JULIAN_ROOT=/opt/julian
PYTHONPATH=/opt/julian:/opt/360-etl
LOCAL_MODEL=
TABLE_GLOBAL=
KAFKA_BROKERS=julian-broker:17811,julian-broker:17812
MODEL_HANDLERS=SpringerHandler,NaicsHandler
CONSUMERS=Article,Org
PRODUCERS=Article,Org
PRODUCER_CHUNKSIZE=100
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=