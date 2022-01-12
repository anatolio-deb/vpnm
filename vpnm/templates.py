""""v2ray configuration templates"""
from typing import Dict

PORT_NON_443: Dict = {
    "outbounds": [
        {
            "mux": {"concurrency": 8, "enabled": False},
            "protocol": "vmess",
            "settings": {
                "vnext": [
                    {
                        "address": "185.46.8.224",
                        "port": 80,
                        "users": [
                            {
                                "alterId": 0,
                                "encryption": "",
                                "flow": "",
                                "id": "d1453437-0014-35fa-a849-cd5554683d72",
                                "level": 8,
                                "security": "auto",
                            }
                        ],
                    }
                ]
            },
            "streamSettings": {
                "network": "tcp",
                "security": "",
                "tcpSettings": {"header": {"type": "none"}},
            },
            "tag": "proxy",
        },
    ],
}

PORT_443: Dict = {
    "outbounds": [
        {
            "mux": {"concurrency": 8, "enabled": False},
            "protocol": "vmess",
            "settings": {
                "vnext": [
                    {
                        "address": "nc.b2rc.ru",
                        "port": 443,
                        "users": [
                            {
                                "alterId": 0,
                                "encryption": "",
                                "flow": "",
                                "id": "d1453437-0014-35fa-a849-cd5554683d72",
                                "level": 8,
                                "security": "auto",
                            }
                        ],
                    }
                ]
            },
            "streamSettings": {
                "network": "ws",
                "security": "tls",
                "tlsSettings": {"allowInsecure": False, "serverName": "nc.b2rc.ru"},
                "wsSettings": {"headers": {"Host": "nc.b2rc.ru"}, "path": "/download"},
            },
            "tag": "proxy",
        },
    ],
}
