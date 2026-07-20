# FrankenVoice Production Deployment Runbook

This document is the long-term operations guide for deploying and maintaining FrankenVoice at:

```text
https://frankenvoice.frankenmint.com
```

The intended production topology is:

```text
Cloudflare DNS and proxy
        |
        v
Alibaba Cloud ECS public IPv4
        |
        v
Host Nginx on ports 80 and 443
        |
        v
http://127.0.0.1:8088
        |
        v
Frontend Nginx container
        |-- serves