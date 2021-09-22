# vpnm
A v2ray client with TUN and DoH support.
## Features
- Forward all your traffic to the v2ray node
- Forward all your DNS queries to the cloudflared DoH through the v2ray node
- No need to configure per-application settings
- No need to configure system proxy settings
## Requirements
You'll need a [VPN Manager](https://vpnm.org/) account in order to use this app.
## Installation
```
curl -sSL https://raw.githubusercontent.com/anatolio-deb/vpnm/main/install.py | sudo python3 -
```
## Usage
You can get help using `vpnm --help` command in your terminal after installation:
```
Usage: vpnm [OPTIONS] COMMAND [ARGS]...

  VPN Manager - secure internet access

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  account     Get information on your account
  connect     Connect to the desired location
  disconnect  Disconnect from the VPN service
  login       Login into VPN Manager account
  logout      Logout from your VPN Manager account
  status      Get the current connection status

```
### Connection shortcuts
After logging into your account you can connect to the desired node in a different ways:
```
Usage: vpnm connect [OPTIONS]

  Connect to the desired location

Options:
  --best    Connect to the best server according to the latency
  --random  Connect to the random server
  --help    Show this message and exit.
```
For example, `vpnm connect --random` will connect you to the random node.

You'll have to choose the node manually if you won't specify any option.
## Uninstall
```
curl -sSL https://raw.githubusercontent.com/anatolio-deb/vpnm/main/install.py | sudo python3 - --uninstall
```
## Dependencies
- [cloudflared](https://github.com/cloudflare/cloudflared) — to forward DoH queries through the TUN interface
- [tun2socks](https://github.com/xjasonlyu/tun2socks) — to forward TCP through the SOCKS proxy
- [vpnmd](https://github.com/anatolio-deb/vpnmd) — to run privileged kernel instructions
- [v2ray-core](https://github.com/v2ray/v2ray-core) — to be free
- netfilter/iptables
- iproute2

## Know issues
The internet connection goes down after a while of being connected to some node.
### Hypothesis
Cloudflared daemon loses connection to the DoH server after some instabillity of v2ray connection on which it relies.
### Workaround
Simply `vpnm disconnect` and `vpnm connect` again.
### Solution
Monitor the DNS availability during an active v2ray connection in a separate thread and reload the cloudflared daemon on DNS response issues.

That implies a constant background work of querying the DNS. The better but complex alternative is to acquire a sort of event system that notifies wether to reload a cloudflared daemon. That relies on tracking the v2ray core instabillity somehow (maybe logs) to predict DNS issues.
