package main

import (
  "net"
  "log"
  "fmt"
  "time"
  "io"
  "os"
)

func create_conn(port int) {
  conn, err := net.Dial("tcp4", fmt.Sprintf(":%d", port))
  if err != nil {
    log.Fatal(fmt.Sprintf("Dial remote failed: %v", err))
  }
  defer conn.Close()


  conn.Write([]byte(fmt.Sprintf("%s\n", time.Now())))
  ticks := time.Tick(1 * time.Second)
  for t := range ticks {
    conn.Write([]byte(fmt.Sprintf("%s\n", t)))
    go func() {
      log.Println("Reading")
      io.Copy(os.Stdout, conn)
    }()
  }
}

func main() {
  port := 3751
  create_conn(port)
}
