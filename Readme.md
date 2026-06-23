# Professor-Centric Genetic Algorithm

## A system designed to generate feasible timetables for dual-delivery teaching environments

This project is a submission for Major Project for Master of Computer Applications. This professor-centric timetable generator is developed using genetic algorithm implemented in python programming language to generate timetables for professors in a dual-delivery teaching environments where online and offline cohorts are taught separately.

Unlike tradional systems that focus on student scheduling and classroom utilization, the proposed algorithm generates a timetable by placing professors in the center of the process. It optimizes the timetable by satisfying academic and operational constraints.

<hr></hr>

### Key Features
- Professor preference-aware scheduling
- Hybrid (Online and Offline) course support
- Professor Wrokload Balancing
- Building and Mode Transition Optimization 
- Student idle gap gap optimization
- Parallel fitness evaluation using multiprocessing
- Clash-free Schedules
- Export schedules in CSV and XLSX file formats

<hr></hr>

### Genetic Algorithm Overview
The timetable generation process follows the standard Genetic Algorithm workflow:

- Initial Population Generation
- Fitness Evaluation
- Tournament Selection
- Heuristic Crossover
- Adaptive Mutation
- Elitism Preservation
- Evolution Until Convergence

The fitness function evaluates timetable quality by applying penalties for constraint violations and rewards feasible scheduling solutions.

<hr></hr>

### System Requirements
#### Software Requirements
- Python 3.14
- Streamlit
- Pandas
- XlsxWriter

#### Installation
#### Running the application

<hr></hr>

### File Upload
![](docs/File_Uploading.gif)

### Results of the Scheduling Process
![](docs/results.gif)

<hr></hr>

