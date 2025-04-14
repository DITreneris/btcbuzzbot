# BTCBuzzBot

<div align="center">
  <img src="static/img/favicon.png" alt="BTCBuzzBot Logo" width="120" height="120">
  <h3>A Bitcoin Price Twitter Bot with Personality</h3>
</div>

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3112/)
[![Flask](https://img.shields.io/badge/Flask-3.0.2-lightgrey)](https://flask.palletsprojects.com/)
[![Twitter API](https://img.shields.io/badge/Twitter%20API-v2-1DA1F2)](https://developer.twitter.com/en/docs/twitter-api)
[![CoinGecko API](https://img.shields.io/badge/CoinGecko-API-yellow)](https://www.coingecko.com/en/api)
[![Heroku](https://img.shields.io/badge/Heroku-Deployed-purple)](https://btcbuzzbot-7c02c485f88e.herokuapp.com/)

## 📊 Overview

**BTCBuzzBot** is an automated Twitter bot that posts real-time Bitcoin price updates combined with motivational quotes or jokes to engage the crypto community. The application includes a full web dashboard for monitoring bot activity, viewing analytics, and controlling operations.

## ✨ Features

- **Automated Bitcoin Price Updates**: Fetches real-time Bitcoin prices from CoinGecko API
- **Content Variety**: Rotates between price updates, motivational quotes, and crypto jokes
- **Twitter Integration**: Posts updates to Twitter via the Twitter API v2
- **Scheduled Operations**: Configurable posting schedule (defaults to 4 times daily)
- **Admin Dashboard**: Web interface for monitoring and controlling bot activity
- **Analytics**: View engagement statistics and price history charts
- **Mobile-Responsive UI**: Modern dark-themed interface built with Bootstrap 5

## 🛠️ Technology Stack

- **Backend**: Python, Flask
- **Database**: SQLite (local) / PostgreSQL (production)
- **APIs**: Twitter API v2, CoinGecko API
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5, Chart.js
- **Deployment**: Heroku

## 📋 Requirements

- Python 3.11+
- Twitter Developer Account with API access
- CoinGecko API key
- Heroku account (for deployment)

## 🚀 Setup & Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/btcbuzzbot.git
   cd btcbuzzbot
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```
   # Twitter API Credentials
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_SECRET=your_access_secret
   
   # CoinGecko API
   COINGECKO_API_KEY=your_coingecko_api_key
   
   # Bot Configuration
   POST_TIMES=08:00,12:00,16:00,20:00
   TIMEZONE=UTC
   
   # Flask Configuration
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   ```

5. **Initialize the database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   flask run
   ```

### Heroku Deployment

1. **Create a Heroku app**
   ```bash
   heroku create btcbuzzbot-yourname
   ```

2. **Configure Heroku environment variables**
   ```bash
   heroku config:set TWITTER_API_KEY=your_api_key
   heroku config:set TWITTER_API_SECRET=your_api_secret
   heroku config:set TWITTER_ACCESS_TOKEN=your_access_token
   heroku config:set TWITTER_ACCESS_SECRET=your_access_secret
   heroku config:set COINGECKO_API_KEY=your_coingecko_api_key
   heroku config:set POST_TIMES=08:00,12:00,16:00,20:00
   heroku config:set TIMEZONE=UTC
   heroku config:set SECRET_KEY=your_secret_key
   ```

3. **Deploy to Heroku**
   ```bash
   git push heroku master
   ```

4. **Initialize the database on Heroku**
   ```bash
   heroku run python init_db.py
   ```

## 🖥️ Web Interface

The application includes a web interface with the following features:

- **Home Page**: View current Bitcoin price, bot statistics, and recent tweets
- **Tweet History**: Browse all tweets with filtering and pagination
- **Admin Panel**: Control bot operation, view error logs, and manage content

### Dashboard URLs

- Home: `/`
- Tweet History: `/posts`
- Admin Panel: `/admin`
- Health Check: `/health`

## 🔄 API Endpoints

The application provides several API endpoints:

- **GET /api/posts**: Retrieve recent posts with pagination and filtering
- **GET /api/stats**: Get bot statistics and Bitcoin price history
- **GET /api/price/refresh**: Manually refresh Bitcoin price data
- **GET /api/price/history**: Get Bitcoin price history for charting

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

BTCBuzzBot is for informational purposes only. The content provided should not be construed as financial advice. Always do your own research before making investment decisions.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Contact

For questions or support, please open an issue on this repository. 