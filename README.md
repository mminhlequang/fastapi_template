# Backend FastAPI deployment:

# Configs
# Just need replace keyword by real value also at .env
Name = {{project_name}}
API Domain = {{domain}}
FRONTEND Domain = {{frontend domain}}
Port = {{port}}



git clone ...

cd {{project_name}}; git pull; docker compose down; docker compose up -d

sudo apt update
sudo apt install nginx -y

sudo nano /etc/nginx/sites-available/{{domain}}.conf
server {
    listen 80;
    server_name {{domain}};

    location / {
        proxy_pass http://127.0.0.1:{{port}};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

sudo ln -s /etc/nginx/sites-available/{{domain}}.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

sudo apt install certbot python3-certbot-nginx -y

sudo certbot --nginx -d {{domain}}
