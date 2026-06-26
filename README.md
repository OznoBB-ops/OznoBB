# OznoBB

# OznoBB - Automated Proxy Config Subscription

🤖 Автоматическое обновление прокси-конфигов каждый час через GitHub Actions.

## 📥 Подписки

| Тип | URL | Описание |
|-----|-----|---------|
| **Verified** | `https://raw.githubusercontent.com/OznoBB-ops/OznoBB/main/subscription.txt` | Только живые + безопасные серверы, проверены с России |
| **Original** | `https://raw.githubusercontent.com/OznoBB-ops/OznoBB/main/original.txt` | Все VLESS + SNI правила без проверок |

## ✨ Особенности

- ✅ **Автоматическое обновление** каждый час
- ✅ **Только VLESS** протокол (Reality приоритет)
- ✅ **Проверка безопасности** — без insecure параметров
- ✅ **Пинг из России** — реальные проверки с Russian nodes check-host.net
- ✅ **Дедупликация** — удаление дубликатов
- ✅ **Зеркала** — fallback на альтернативные источники
- ✅ **Форматирование** — `🇷🇺RU#1`, `🇩🇪DE#1` и т.д.

## 📊 Источники

**Основные:**
- zieng2/wl
- igareck/vpn-configs-for-russia

**Зеркала:**
- GitHub, GitLab, Codeberg, Gitea, SourceHut, Bitbucket, Githack

## 🔒 Безопасность

Только конфиги с:
- `security=reality` (всегда)
- `security=tls` без `insecure=1`

Удаляются:
- ❌ `insecure=1`
- ❌ `allowInsecure=1`
- ❌ `security=none`

## 📝 Использование

В клиенте (Hiddify, Sing-Box и т.д.) добавьте подписку:

