# Backend FastAPI deployment:

git clone ...

cd startomation_api; git pull; docker compose down; docker compose up -d

sudo apt update
sudo apt install nginx -y

sudo nano /etc/nginx/sites-available/api.genqr.pro.conf
server {
    listen 80;
    server_name api.genqr.pro;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

sudo ln -s /etc/nginx/sites-available/api.genqr.pro.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

sudo apt install certbot python3-certbot-nginx -y

sudo certbot --nginx -d api.genqr.pro
