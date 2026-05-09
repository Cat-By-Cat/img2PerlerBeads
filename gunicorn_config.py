import multiprocessing

bind = "0.0.0.0:8666"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/var/log/pindou/access.log"
errorlog = "/var/log/pindou/error.log"
loglevel = "info"
