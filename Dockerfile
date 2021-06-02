FROM python:3.9
RUN apt update && apt install git -y
RUN pip install --upgrade pip
RUN pip install poetry pytest
WORKDIR /code
RUN mkdir vpnm tests
COPY pyproject.toml .
COPY poetry.lock .
COPY install.py .
COPY vpnm vpnm
COPY tests tests
RUN rm -rf vpnm/__pycache__
RUN rm -rf tests/__pycache__
RUN poetry export --dev --without-hashes -f requirements.txt --output requirements.txt
RUN pip install -r requirements.txt
# RUN mkdir -p /dev/net
# RUN mknod /dev/net/tun c 10 200
# RUN chmod 600 /dev/net/tun
RUN mkdir /root/.config
CMD ["pytest", "-v"]