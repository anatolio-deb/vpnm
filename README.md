# vpnm

An alternative [VPN Manager](https://vpn-m.com/) client for Linux CLI.

## Dependencies

- [cloudflared](https://github.com/cloudflare/cloudflared) — to forward DoH queries through the TUN interface
- [tun2socks](https://github.com/xjasonlyu/tun2socks) — to forward TCP through the SOCKS proxy
- [vpnmd](https://github.com/anatolio-deb/vpnmd) — to run privileged kernel instructions
- [v2gen](https://github.com/iochen/v2gen) — to manage servers
- [v2ray-core](https://github.com/v2ray/v2ray-core) — to be free

## To-do

- Automated testing

# Tests

Tested manually on Ubuntu Linux 18.04 bionic.