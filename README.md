<div align="center">
  <h1>Fleet Simulator: UMINHO AI 25/26</h1>
  <p><strong>A comprehensive fleet simulation for analyzing EVs and Gas vehicles in urban environments.</strong></p>

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/Language-Python_3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Tkinter](https://img.shields.io/badge/GUI-Tkinter-003B57?logo=python&logoColor=white)](https://docs.python.org/3/library/tkinter.html)
  [![GDAL](https://img.shields.io/badge/Library-GDAL-1D365D?logo=osgeo&logoColor=white)](https://gdal.org/)
</div>

**Fleet Simulator** is a desktop application developed for the Artificial Intelligence class (Maio, 2026) at Universidade do Minho. It provides a robust environment to simulate and optimize fleet operations, comparing the efficiency and environmental impact of Electric Vehicles (EVs) versus Gas Vehicles using real-world map data.

## Overview

We built this project to simulate and analyze the complexities of urban fleet management. **Fleet Simulator** models traffic conditions, hotspot demands, charging/fueling logistics, and vehicle dispatching. It demonstrates how AI strategies can be used to optimize routes and manage a mixed fleet of vehicles efficiently across large city maps (e.g., Braga).

## Screenshots

<p align="center">
  <img src="images/app/mainScreen.png" alt="Main Screen" width="400" style="border-radius: 10px; margin: 10px;" />
  <img src="images/app/map.png" alt="Map View" width="400" style="border-radius: 10px; margin: 10px;" />
</p>
<p align="center">
  <img src="images/app/metrics.png" alt="Metrics Panel" width="400" style="border-radius: 10px; margin: 10px;" />
  <img src="images/app/benchmarkResults.png" alt="Benchmark Results" width="400" style="border-radius: 10px; margin: 10px;" />
</p>

## Key Features

### Realistic Map Data
- **GDAL Integration:** Uses real-world mapping data caching for node generation, edge mapping, and realistic coordinate systems.

### Dynamic Fleet Simulation
- **Mixed Fleet Engine:** Models both Electric Vehicles (EVs) and Gas Vehicles, natively handling battery/fuel constraints and charging speeds.
- **Traffic & Hotspots:** Simulates varying traffic conditions and demand hotspots that shift dynamically throughout the day.

### Advanced Dispatching
- **AI Routing:** Assigns pending ride requests and manages dynamic routing based on changing environments.
- **Station Management:** Simulates charging station usage, queuing, and unexpected stochastic station failures.

## Tech Stack

The project was built using:

### **Application & Simulation Engine**
- **Language:** [Python](https://www.python.org/)
- **GUI Framework:** Tkinter for displaying vehicle metrics, map views, and weather states.
- **Geographic Data:** GDAL (native C Library dependency).
- **Data Handling:** Custom simulation engine with deterministic and stochastic components, tracking detailed continuous simulation stats.

## The Team

Fleet Simulator was created by:

| Member | Institution | Role / Study Area |
| :--- | :--- | :--- |
| **[Herculano Esteves](https://github.com/Herculano-Esteves)** (a107293) | Universidade do Minho | Software Engineering |
| **[Nuno Fernandes](https://github.com/nunom27)** (a107317) | Universidade do Minho | Software Engineering |
| **[Salomé Faria](https://github.com/faria-s)** (a108487) | Universidade do Minho | Software Engineering |
| **[Tiago Alves](https://github.com/Tiagohvv)** (a106883) | Universidade do Minho | Software Engineering |

## Getting Started

Follow these instructions to set up the project locally.

### Prerequisites
- **Python 3.9+**
- **GDAL (C Library)**: Must be installed natively on your system (e.g., `sudo apt-get install gdal-bin libgdal-dev` on Ubuntu/Debian).

### 1. Clone the Repository
```bash
git clone https://github.com/Herculano-Esteves/AI-25-26.git
cd AI-25-26
```

### 2. Setup Environment
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/MacOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install python dependencies
pip install -r requirements.txt
```

### 3. Run the Simulation
Launch the primary GUI and simulation engine.
```bash
python main.py
```

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details (if applicable).
