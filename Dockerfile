FROM python:3.11-slim

WORKDIR /app

# Точка (tochka.com) отдаёт сертификат, подписанный Минцифры РФ
# (Russian Trusted Root/Sub CA) — его нет в стандартном доверенном
# наборе Debian, ставим руками, иначе SSL-хендшейк падает.
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL -o /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
       https://gu-st.ru/content/Other/doc/russian_trusted_root_ca_pem.crt \
    && curl -fsSL -o /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt \
       https://gu-st.ru/content/Other/doc/russian_trusted_sub_ca_pem.crt \
    && update-ca-certificates \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# requests по умолчанию использует свой пакет certifi, а не системное
# хранилище — явно указываем ему доверять системному бандлу.
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
