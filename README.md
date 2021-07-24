# vpnm

An alternative [VPN Manager](https://vpn-m.com/) client for Linux CLI.

# **Installation**

```
curl -sSL https://raw.githubusercontent.com/anatolio-deb/vpnm/main/install.py | sudo python3 -
```

## Dependencies

- [cloudflared](https://github.com/cloudflare/cloudflared) — to forward DoH queries through the TUN interface
- [tun2socks](https://github.com/xjasonlyu/tun2socks) — to forward TCP through the SOCKS proxy
- [vpnmd](https://github.com/anatolio-deb/vpnmd) — to run privileged kernel instructions
- [v2gen](https://github.com/iochen/v2gen) — to manage servers
- [v2ray-core](https://github.com/v2ray/v2ray-core) — to be free
- netfilter/iptables
- iproute2

## Uninstall

```
curl -sSL https://raw.githubusercontent.com/anatolio-deb/vpnm/main/install.py | sudo python3 - --uninstall
```

# Testing

**Caution**: tested manually on Ubuntu 18.04 bionic.

Automated testing is currently in development.

## Concepts

Vpnm is a software that relies it's behaviour on many different factors such as:

- User authentication state
- Session state
- Vpnm daemon state

All these states should reflect in the relevant test cases as followed:

1. Test case with a negative state
2. Test case with a positive state

Every test case should cover as much codebase as possible to approve an expected behaviour on each state.
