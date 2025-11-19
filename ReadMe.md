# ListingLens - Property Intelligence Dashboard

**ListingLens** is an enterprise-grade property intelligence platform designed to transform unstructured real estate data into actionable insights. By leveraging advanced web scraping technologies and state-of-the-art AI, ListingLens automates the extraction, processing, and analysis of property listings, empowering users with a structured and queryable dataset.

---

## 🌟 Key Features

*   **AI-Powered Extraction**: Utilizes Google Gemini AI to intelligently parse complex and unstructured HTML content from property listings into standardized JSON data.
*   **Automated Scraping**: Features a robust Selenium-based scraping engine capable of navigating dynamic websites and handling user interactions to retrieve complete listing details.
*   **Real-time Processing**: Implements an asynchronous task queue architecture using Celery and Redis to handle scraping and data processing tasks efficiently in the background.
*   **Interactive Dashboard**: Offers a modern, user-friendly web interface built with Next.js for submitting URLs, monitoring extraction progress, and analyzing historical data.
*   **Scalable Architecture**: Built on a microservices architecture with Docker, separating concerns between the API, workers, database, and frontend for maximum scalability and maintainability.
*   **Data Export**: Allows users to easily export processed data into CSV format for further analysis in external tools.

---

## 🏗️ System Architecture

ListingLens is composed of several decoupled services orchestrated via Docker Compose:

### 1. Frontend Service (`frontend`)
*   **Tech Stack**: Next.js 14 (App Router), TypeScript, Tailwind CSS.
*   **Role**: The user interface. It communicates with the Backend API to submit tasks and fetch data.
*   **Features**:
    *   **Dashboard**: Real-time view of current scraping sessions.
    *   **History**: Archive of all previously scraped properties.
    *   **Apple-inspired UI**: Clean, minimalist design with blue/white/black theming and subtle animations.

### 2. Backend API Service (`backend`)
*   **Tech Stack**: FastAPI, Python 3.11, SQLAlchemy (Async), Pydantic.
*   **Role**: The central orchestrator. It exposes RESTful endpoints for the frontend, manages database interactions, and dispatches heavy lifting tasks to the Worker.

### 3. Worker Service (`worker`)
*   **Tech Stack**: Celery, Python.
*   **Role**: The powerhouse. It executes background tasks asynchronously to prevent blocking the API.
*   **Responsibilities**:
    *   Receiving scraping tasks from Redis.
    *   Controlling the Selenium WebDriver.
    *   Sending raw HTML to the Gemini AI service for extraction.
    *   Saving structured results to the database.

### 4. Database Service (`db`)
*   **Tech Stack**: PostgreSQL.
*   **Role**: The persistent storage layer. Stores user data, raw listing information, and processed structured data.

### 5. Message Broker (`redis`)
*   **Tech Stack**: Redis.
*   **Role**: Acts as the message broker for Celery, managing the queue of tasks between the Backend and the Worker. Also serves as a cache if needed.

### 6. Scraping Engine (`selenium-hub` & `chrome`)
*   **Tech Stack**: Selenium Grid, Standalone Chrome.
*   **Role**: Provides a headless browser environment for the Worker to navigate websites and render JavaScript-heavy content.

### 7. AI Service Integration
*   **Provider**: Google Gemini.
*   **Role**: Analyzes raw HTML content extracted by the scraper and converts it into a structured format (JSON) containing fields like price, location, specifications, and description.

---

## 🔄 Process Flow

1.  **Task Submission**: A user pastes a list of property URLs into the Frontend dashboard.
2.  **API Request**: The Frontend sends these URLs to the Backend API (`POST /listings/scrape`).
3.  **Queueing**: The Backend creates a task for each URL and pushes it to the Redis message queue.
4.  **Execution**: The Worker picks up a task from the queue.
5.  **Scraping**: The Worker commands the Selenium Grid to launch a Chrome instance, navigate to the URL, and interact with the page (e.g., clicking "Show Phone Number" buttons) to ensure all data is visible.
6.  **Extraction**: The Worker captures the page's HTML and sends it to the Gemini AI service.
7.  **Structuring**: Gemini parses the HTML and returns structured data (JSON).
8.  **Storage**: The Worker saves the structured data into the PostgreSQL database.
9.  **Notification**: The Frontend polls the Backend for updates and displays the new data to the user as soon as it's ready.

---

## 🚀 Getting Started

### Prerequisites

*   **Docker Desktop**: Required to run the containerized application.
    *   [Mac (Apple Silicon)](https://desktop.docker.com/mac/main/arm64/Docker.dmg)
    *   [Mac (Intel)](https://desktop.docker.com/mac/main/amd64/Docker.dmg)
    *   [Windows/Linux](https://www.docker.com/products/docker-desktop/)
*   **Google Gemini API Key**: Essential for the AI extraction feature.

### Installation & Running

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/WeldonTan/ListingLens.git
    cd ListingLens
    ```

2.  **Configure Environment**
    Create a `.env` file in the root directory (or use the helper script below) and add your Gemini API key:
    ```env
    GEMINI_API_KEY=your_api_key_here
    ```

3.  **Run the Start Script (Recommended)**
    This script automates the setup process, checks for Docker, and starts the services.
    ```bash
    ./start.sh
    ```
    *Note: If you encounter permission issues, run `chmod +x start.sh` first.*

4.  **Manual Start (Alternative)**
    If you prefer running Docker commands directly:
    ```bash
    docker compose up --build -d
    ```

### 🐳 Docker Build Process

If you modify the code and need to rebuild the Docker containers to reflect your changes:

1.  **Full Rebuild (Recommended)**
    To rebuild all services and detach:
    ```bash
    docker compose up --build -d
    ```

2.  **Specific Service Rebuild**
    If you only changed code in one service (e.g., the frontend), you can rebuild just that container to save time:
    ```bash
    docker compose up --build -d frontend
    ```
    *Replace `frontend` with `backend` or `worker` as needed.*

3.  **Clean Rebuild**
    If you encounter issues, you can force a clean build by removing the containers and images first:
    ```bash
    docker compose down
    docker compose up --build -d
    ```

### Accessing the Application

*   **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
*   **Backend API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Selenium Grid Console**: [http://localhost:4444](http://localhost:4444)

---

## 🔮 Future Enhancements

We are constantly working to improve ListingLens. Here's what's on our roadmap:

*   **Advanced Analytics**: Integration of more detailed market analysis tools, including price trend visualization and comparative market analysis (CMA).
*   **Multi-Platform Support**: Extending scraper capabilities to support additional property listing platforms beyond the current set.
*   **User Authentication**: Implementing a robust user authentication system (e.g., Auth0 or NextAuth) to support multi-user environments and personalized settings.
*   **Notification System**: Adding email or Slack notifications to alert users when new listings matching their criteria are found.
*   **Enhanced AI Capabilities**: Upgrading to more advanced AI models for even better extraction accuracy and the ability to infer missing data points.
*   **API Rate Limiting**: Implementing rate limiting on the backend to ensure system stability and prevent abuse.

---

## 🛠️ Development

To contribute or make changes to the codebase:

### Backend Development
The backend is located in the `backend/` directory.
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
The frontend is located in the `frontend/` directory.
```bash
cd frontend
npm install
npm run dev
```

---

## 📝 License

This project is licensed under the MIT License.
