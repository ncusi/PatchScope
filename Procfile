release: curl https://dagshub.com/ncusi/PatchScope/raw/main/data/examples/stats/tensorflow.timeline.purpose-to-type.json -o data/examples/stats/tensorflow.timeline.purpose-to-type.json
web: panel serve --address="0.0.0.0" --port=$PORT src/diffinsights_web/apps/contributors.py src/diffinsights_web/apps/author.py --allow-websocket-origin="patchscope-9d05e7f15fec.herokuapp.com"
