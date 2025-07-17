#!/bin/bash

echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "🔄 Restarting facebook-scraper service..."
sudo systemctl restart facebook-scraper

echo "✅ Service reloaded and restarted!"
echo "📊 Service status:"
sudo systemctl status facebook-scraper --no-pager -l 