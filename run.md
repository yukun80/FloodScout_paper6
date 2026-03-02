PYTHONPATH=src python -m floodscout.cli crawl-history \
--cities 宝鸡 \
--start-date 2024-07-10 \
--end-date 2024-12-31 \
--slice-unit week \
--weibo-cookie-file data/input/weibo_cookie.txt \
--crawler weibo \
--crawler-mode api \
--limit 30 \
--max-pages 5