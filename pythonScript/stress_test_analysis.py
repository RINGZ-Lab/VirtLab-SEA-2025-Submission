"""
Stress Test Analysis Script for Scalability Evaluation
"""

import json
import os
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import seaborn as sns
from pathlib import Path

class StressTestAnalyzer:
    def __init__(self, base_dir="."):
        self.base_dir = Path(base_dir)
        self.results = {}
        
    def analyze_file(self, filepath):
        """Analyze a single JSON file and extract metrics."""
        metrics = {
            'total_steps': 0,
            'total_rescues': 0,
            'unique_rooms_visited': set(),
            'agent_steps': defaultdict(int),
            'agent_visits': defaultdict(lambda: defaultdict(int)),
            'victims_found': 0,
            'simulation_completed': False,
            'final_time': 0,
            'agent_actions': 0,
            'total_communications': 0,
            'communication_events': [],
        }
        
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    if 'time' in rec:
                        current_time = rec['time']
                        if current_time > 0:
                            metrics['final_time'] = max(metrics['final_time'], current_time)
                            metrics['total_steps'] = current_time
                    
                    if 'world_state' in rec:
                        ws = rec['world_state']
                        if isinstance(ws, dict):
                            if 'total rescues' in ws:
                                metrics['total_rescues'] = ws['total rescues']
                            
                            rd = ws.get('room_descriptions')
                            if isinstance(rd, list):
                                
                                
                                for room in rd:
                                    metrics['unique_rooms_visited'].add(room)
                    
                    if 'agent' in rec and 'command' in rec:
                        af = rec['agent']
                        if isinstance(af, dict):
                            agent_id = af.get('entity_id') or af.get('name')
                            agent_name = af.get('name') or f"agent_{agent_id}"
                        else:
                            agent_name = str(af)
                        
                        metrics['agent_steps'][agent_name] += 1
                        metrics['agent_actions'] += 1
                    
                    if 'parsed_response' in rec and 'agent' in rec:
                        af = rec['agent']
                        if isinstance(af, dict):
                            agent_id = af.get('entity_id') or af.get('name')
                            agent_name = af.get('name') or f"agent_{agent_id}"
                        else:
                            agent_name = str(af)
                        
                        pr_raw = rec['parsed_response']
                        if isinstance(pr_raw, str):
                            try:
                                pr = json.loads(pr_raw)
                            except json.JSONDecodeError:
                                pr = {}
                        elif isinstance(pr_raw, dict):
                            pr = pr_raw
                        else:
                            pr = {}
                        
                        loc = pr.get('move')
                        if isinstance(loc, dict):
                            loc = loc.get('move') or next(iter(loc.values()), None)
                        if isinstance(loc, str):
                            metrics['agent_visits'][agent_name][loc] += 1
                    
                    if 'parsed_response' in rec:
                        parsed = rec['parsed_response']
                        if isinstance(parsed, str):
                            try:
                                parsed_data = json.loads(parsed)
                            except json.JSONDecodeError:
                                parsed_data = {}
                        else:
                            parsed_data = parsed
                        
                        if 'communicate' in parsed_data:
                            metrics['communication_attempts'] += 1
                            metrics['total_communications'] += 1
                            
                            comm_event = {
                                'time': rec.get('time', 0),
                                'agent': rec.get('agent', {}),
                                'targets': parsed_data['communicate']
                            }
                            metrics['communication_events'].append(comm_event)
                            
                            agent_info = rec.get('agent', {})
                            initiator = agent_info.get('role', 'unknown')
                            targets = parsed_data['communicate']
                            if isinstance(targets, list):
                                for target in targets:
                                    interaction_key = f"{initiator}->{target}"
                                    metrics['agent_interactions'][interaction_key] += 1
                            elif isinstance(targets, str):
                                interaction_key = f"{initiator}->{targets}"
                                metrics['agent_interactions'][interaction_key] += 1
                    if 'action_result' in rec:
                        ar = rec['action_result']
                        if isinstance(ar, dict):
                            success = ar.get('success', False)
                            reason = ar.get('reason', '')
                            if 'communication' in str(ar).lower() or 'communicate' in reason.lower():
                                if success:
                                    metrics['communication_successes'] += 1
                                else:
                                    metrics['communication_failures'] += 1

                    if 'time' in rec and rec['time'] > 0:
                        metrics['simulation_completed'] = True
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")
            return None

        metrics['unique_rooms_count'] = len(metrics['unique_rooms_visited'])
        metrics['unique_rooms_visited'] = list(metrics['unique_rooms_visited'])
        
        if metrics['communication_attempts'] > 0:
            metrics['communication_success_rate'] = metrics['communication_successes'] / metrics['communication_attempts']
        
        num_agents = len(metrics['agent_steps'])
        if num_agents > 0:
            metrics['communication_attempts_per_agent'] = metrics['communication_attempts'] / num_agents
            metrics['communication_successes_per_agent'] = metrics['communication_successes'] / num_agents
            metrics['communication_failures_per_agent'] = metrics['communication_failures'] / num_agents
            metrics['total_communications_per_agent'] = metrics['total_communications'] / num_agents
        
        metrics['agent_steps'] = dict(metrics['agent_steps'])
        
        return metrics
    
    def analyze_all_files(self):
        """Analyze all JSON files in the Stree_Simulation directory structure."""
        complexity_levels = ['EasyMap', 'MediumMap', 'HardMap']
        agent_counts = ['TwoAgents', 'ThreeAgents', 'FourAgents', 'FiveAgents']
        
        for complexity in complexity_levels:
            complexity_path = self.base_dir / "Stree_Simulation" / complexity
            if not complexity_path.exists():
                continue

            complexity_display = complexity.replace('Map', ' Complexity')
            self.results[complexity_display] = {}
            
            for agent_count in agent_counts:
                agent_path = complexity_path / agent_count
                if not agent_path.exists():
                    continue
                agent_count_display = agent_count.replace('Agents', ' Agents')
                self.results[complexity_display][agent_count_display] = []

                json_files = list(agent_path.glob("*.json"))
                
                for json_file in json_files:
                    print(f"Analyzing: {json_file}")
                    metrics = self.analyze_file(json_file)
                    if metrics:
                        metrics['file_path'] = str(json_file)
                        metrics['complexity'] = complexity_display
                        metrics['agent_count'] = agent_count_display
                        metrics['num_agents'] = len(metrics['agent_steps'])
                        
                        self.results[complexity_display][agent_count_display].append(metrics)
    
    def calculate_aggregate_metrics(self):
        """Calculate aggregate metrics for each configuration."""
        aggregate_results = []
        
        for complexity, agent_data in self.results.items():
            for agent_count, runs in agent_data.items():
                if not runs:
                    continue
                avg_metrics = {
                    'complexity': complexity,
                    'agent_count': agent_count,
                    'num_runs': len(runs),


                    'avg_total_steps': np.mean([r['total_steps'] for r in runs]),
                    'avg_total_rescues': np.mean([r['total_rescues'] for r in runs]),
                    'avg_unique_rooms': np.mean([r['unique_rooms_count'] for r in runs]),
                    'avg_simulation_time': np.mean([r['final_time'] for r in runs]),
                    'avg_total_communications': np.mean([r['total_communications'] for r in runs]),
                    'avg_communication_attempts_per_agent': np.mean([r['communication_attempts_per_agent'] for r in runs]),


                    'std_total_steps': np.std([r['total_steps'] for r in runs]),
                    'std_total_rescues': np.std([r['total_rescues'] for r in runs]),
                    'std_unique_rooms': np.std([r['unique_rooms_count'] for r in runs]),
                    'std_simulation_time': np.std([r['final_time'] for r in runs]),
                    'std_total_communications': np.std([r['total_communications'] for r in runs]),
                }
                
                aggregate_results.append(avg_metrics)
        
        return aggregate_results

    
    def save_detailed_results(self, filename='detailed_results.csv'):
        """Save detailed results to CSV."""
        aggregate_results = self.calculate_aggregate_metrics()
        df = pd.DataFrame(aggregate_results)
        df.to_csv(filename, index=False)
        print(f"Detailed results saved to {filename}")
        
        return df

def main():
    analyzer = StressTestAnalyzer()
    analyzer.analyze_all_files()
    for complexity in ['Easy Complexity', 'Medium Complexity', 'Hard Complexity']:
        print(f"\n{complexity}:")
        if complexity in analyzer.results:
            for agent_count, runs in analyzer.results[complexity].items():
                if runs:
                    avg_rescues = np.mean([r['total_rescues'] for r in runs])
                    avg_steps = np.mean([r['total_steps'] for r in runs])
                    avg_communications = np.mean([r['total_communications'] for r in runs])
                    avg_task_balance = np.mean([r['task_distribution_balance'] for r in runs])

if __name__ == "__main__":
    main()
