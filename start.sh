#!/bin/bash

(node vrm/server.js | sed 's/^/[Node] /') &

NODE_PID=$!

clean() {
  echo "Stopping node server..."
  kill $NODE_PID
  exit
}

trap cleanup INT TERM

sleep 2

(python3 main.py | sed 's/^/[Python] /')

cleanup
