FROM ubuntu:latest
RUN apt-get update
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y unzip wget curl software-properties-common git iproute2 iptables systemd 
RUN apt-add-repository -y ppa:deadsnakes/ppa
RUN apt-get install -y python3.9 python3-pip
RUN python3.9 -m pip install --upgrade pip
RUN python3.9 -m pip install poetry pytest
# RUN wget -q https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh
COPY install-release.sh .
RUN bash install-release.sh
RUN wget -q https://bin.equinox.io/c/VdrWdbjqyF/cloudflared-stable-linux-amd64.deb
RUN dpkg -i cloudflared-stable-linux-amd64.deb
WORKDIR /usr/local/bin/
RUN wget -q https://github.com/iochen/v2gen/releases/download/v2.0.1/v2gen_amd64_linux
RUN chmod +x v2gen_amd64_linux
RUN wget -q https://github.com/xjasonlyu/tun2socks/releases/download/v2.2.0/tun2socks-linux-amd64.zip
RUN unzip tun2socks-linux-amd64.zip
WORKDIR /code
RUN mkdir vpnm tests
COPY pyproject.toml .
COPY poetry.lock .
COPY install.py .
COPY vpnm vpnm
COPY tests tests
COPY server.py .
RUN rm -rf vpnm/__pycache__
RUN rm -rf tests/__pycache__
RUN poetry export --dev --without-hashes -f requirements.txt --output requirements.txt
RUN pip install -r requirements.txt
RUN mkdir /root/.config
CMD ["pytest", "-v"]