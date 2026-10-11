# Deployment checklist (VPS + Caddy + DuckDNS + Telegram)

## 0. Before you start
- Set a **monthly spending limit** in the OpenAI dashboard.
- Create a **separate production Telegram bot** in @BotFather (keep your dev bot for local testing; two n8n instances on one bot overwrite each other's webhook).
- Create a **dedicated demo Gmail/Calendar account** for n8n.
- Make sure `server/alembic/versions/` (your migration files) is committed to the repo.

## 1. Repo layout (repo root)
```
docker-compose.yml   Caddyfile   .env.example   .gitignore   DEPLOY.md
.github/workflows/deploy.yml
server/   (Dockerfile, requirements.txt, alembic.ini, alembic/, api/, graph/, db/, .dockerignore, .env.example)
```
Commit `.env.example` files only; real `.env` files stay out of git.

## 2. Create the server
1. Rent an Ubuntu 24.04 LTS VPS (2 GB RAM is comfortable). Add your SSH public key during creation.
2. Connect: `ssh root@SERVER_IP`
3. Create a non-root user and give it your key:
   ```bash
   adduser deploy && usermod -aG sudo deploy
   mkdir -p /home/deploy/.ssh && cp ~/.ssh/authorized_keys /home/deploy/.ssh/
   chown -R deploy:deploy /home/deploy/.ssh
   ```
4. Log in as `deploy`, then install Docker and the firewall:
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker deploy      # log out and back in afterwards
   sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
   sudo ufw enable
   ```
5. Disable password SSH login: set `PasswordAuthentication no` in `/etc/ssh/sshd_config`, then `sudo systemctl restart ssh`.

## 3. Free domain (DuckDNS)
1. Sign in at duckdns.org, create a subdomain (e.g. `clinic-demo`), set its IP to `SERVER_IP`.
2. Check: `nslookup clinic-demo.duckdns.org` returns your server IP.

## 4. First deploy (manual)
```bash
cd ~ && git clone https://github.com/YOUR_USER/YOUR_REPO.git app && cd app
cp .env.example .env && nano .env                 # DOMAIN, passwords, N8N_ENCRYPTION_KEY
cp server/.env.example server/.env && nano server/.env   # OpenAI key, n8n URLs
docker compose up -d --build
docker compose ps
docker compose logs migrate api --tail=50
```
(Private repo: add a read-only deploy key on the server and clone over SSH.)

**Open `https://YOUR_DOMAIN` immediately and create the n8n owner account.** Until you do, anyone who finds the URL could claim it. Turn on 2FA afterwards.

## 5. Move your workflow into the server n8n
1. In local n8n export each workflow (menu -> Download) and import it on the server.
2. **Re-create credentials** (Telegram prod bot token, Gmail, Calendar, OpenAI if used). They can't be moved because the encryption key is different.
3. In HTTP Request nodes that call your API, use `http://api:8000/chat` (not localhost, not ngrok).
4. Google Cloud Console -> OAuth client -> add redirect URI: `https://YOUR_DOMAIN/rest/oauth2-credential/callback`.
   - Check your OAuth consent screen status. As far as I know, refresh tokens for apps left in "Testing" expire after about 7 days, which would silently break the calendar/email nodes. Verify this in Google's docs and publish the app if needed.
5. Activate the workflow. The Telegram Trigger registers its webhook automatically. Verify:
   `https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo` (the URL should be your domain, with no errors).
6. Put `chat_id` into the request as `thread_id`, and use production `/webhook/` paths in `server/.env`.

## 6. RAG data
The `chroma_data` volume starts empty. Run your ingestion script inside the container, for example:
`docker compose exec api python PATH/TO/YOUR_INGEST_SCRIPT.py`

## 7. CI/CD (GitHub Actions)
1. On your PC: `ssh-keygen -t ed25519 -f gh_deploy -N ""`
2. Append `gh_deploy.pub` to `/home/deploy/.ssh/authorized_keys` on the server.
3. GitHub repo -> Settings -> Secrets and variables -> Actions -> add:
   - `SSH_HOST`: server IP
   - `SSH_USER`: `deploy`
   - `SSH_KEY`: contents of the private file `gh_deploy`
   - `SSH_KNOWN_HOSTS`: output of `ssh-keyscan -H SERVER_IP`
4. Push to `main`. CI validates and builds, then CD pulls and restarts on the server.
5. Delete `gh_deploy` from your PC afterwards.

## 8. Backups (cron on the server)
```bash
mkdir -p ~/backups && crontab -e
# add:
0 3 * * * cd ~/app && docker compose exec -T db pg_dump -U postgres AI_scheduling | gzip > ~/backups/db-$(date +\%F).sql.gz
```
Also back up the `n8n_data` volume and your `N8N_ENCRYPTION_KEY`.

## 9. Test
- Fresh Telegram account -> `/start` -> book an appointment end to end.
- `docker compose down && docker compose up -d` (no `-v`): the conversation should resume (state is in Postgres).
- Reboot the VPS: everything should come back by itself (`restart: unless-stopped`).
