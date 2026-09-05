FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY server.py /srv/

# Self-signed cert with a backdated notBefore (configurable account age).
# openssl req ignores default_startdate, so we self-sign through `openssl ca`
# which honors -startdate / -enddate explicitly.
ARG ACCOUNT_AGE_DAYS=800
RUN mkdir -p /srv/ca && touch /srv/ca/index.txt && echo 1000 > /srv/ca/serial \
    && printf '[ ca ]\ndefault_ca = ca_default\n[ ca_default ]\ndatabase = /srv/ca/index.txt\nserial = /srv/ca/serial\nnew_certs_dir = /srv/ca\nprivate_key = /srv/key.pem\ncertificate = /srv/cert.pem\ndefault_md = sha256\npolicy = policy_any\n[ policy_any ]\ncommonName = supplied\n[ req ]\ndistinguished_name = dn\nprompt = no\n[ dn ]\nCN = decoytell\n' > /srv/ca.cnf \
    && START=$(date -u -d "${ACCOUNT_AGE_DAYS} days ago" +%y%m%d%H%M%S)Z \
    && END=$(date -u -d "3650 days" +%y%m%d%H%M%S)Z \
    && openssl req -new -newkey rsa:2048 -nodes -keyout /srv/key.pem -out /srv/req.pem -subj "/CN=decoytell" -config /srv/ca.cnf \
    && openssl ca -selfsign -config /srv/ca.cnf -keyfile /srv/key.pem -in /srv/req.pem -out /srv/cert.pem -startdate "$START" -enddate "$END" -batch \
    && rm -rf /srv/ca /srv/req.pem /srv/ca.cnf

ENV PORT=8443 BANNER="Apache/2.4.54 (Debian)" TIMING_MS=0 MONITORING=immediate
EXPOSE 8443
CMD ["python", "/srv/server.py"]