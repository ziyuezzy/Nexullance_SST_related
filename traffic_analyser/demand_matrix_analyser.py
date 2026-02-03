import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys
import os

# Handle both relative and absolute imports
try:
    from .helpers import *
except ImportError:
    from helpers import *

class demand_matrix_analyser():
    """
    Traffic analyzer for aggregated demand matrix statistics from SST simulations.
    This class handles the newer CSV format where traffic is already aggregated over sampling intervals,
    rather than individual packet events.
    """
    
    def __init__(self, input_csv_path, V, D, topo_name, EPR, Cap_core, Cap_access, suffix, 
                 use_per_interval=True):
        """
        Initialize the demand matrix analyzer.
        
        Args:
            input_csv_path: Path to the CSV file with demand matrix statistics
            V: Number of vertices in the topology
            D: Diameter or degree parameter
            topo_name: Name of the topology
            EPR: Endpoints per router
            Cap_core: Core link capacity in Gbps
            Cap_access: Access link capacity in Gbps
            suffix: Suffix for identification
            use_per_interval: If True (default), extract per-interval traffic by computing 
                            differences between consecutive accumulated matrices. 
                            If False, use accumulated values directly.
        """
        self.num_EPs = V * EPR
        self.topo_name = topo_name
        self.V = V
        self.D = D
        self.EPR = EPR
        self.Cap_core = Cap_core
        self.Cap_access = Cap_access
        self.topo_full_name = f"({V}, {D})_{topo_name}_{EPR}_EPR"
        self.suffix = suffix
        self.use_per_interval = use_per_interval
        
        # Read the CSV file
        self.raw_data = pd.read_csv(input_csv_path, skipinitialspace=True)
        
        # Parse the demand matrix data
        self.original_interval_ns, self.demand_matrices = self._parse_demand_matrix()
        
        # Extract parameters from config or filename
        self.params = {
            'BENCH': 'Unknown',
            'EPR': EPR,
            'ROUTING': 'source_routing',
            'V': V,
            'D': D,
            'TOPO': topo_name,
            'SUFFIX': suffix
        }
        
        # Try to extract additional params from filename
        filename = os.path.basename(input_csv_path)
        extracted = extract_config_from_filename(filename)
        self.params.update({k: v for k, v in extracted.items() if v is not None})
        
    def _parse_demand_matrix(self):
        """
        Parse the raw CSV data into demand matrices.
        Returns:
            tuple: (sampling_interval_ns, list of (timestamp_ns, demand_matrix) tuples)
        """
        # Extract source IDs from ComponentName
        # Try format: 'offered_load_X'
        src_ids = self.raw_data['ComponentName'].str.extract(r'offered_load_(\d+)')[0]
        
        # If that fails, try alternative format: 'nicX:...'
        if src_ids.isna().all():
            src_ids = self.raw_data['ComponentName'].str.extract(r'nic(\d+):')[0]
        
        # If still no match, try extracting from any format with numbers
        if src_ids.isna().any():
            raise ValueError("Unable to extract source IDs from ComponentName")
        
        self.raw_data['src_id'] = src_ids.astype(int)
        
        # Extract destination IDs from StatisticSubId (dst_Y)
        self.raw_data['dst_id'] = self.raw_data['StatisticSubId'].str.extract(r'dst_(\d+)')[0].astype(int)
        
        # Get unique timestamps (SimTime values)
        timestamps = sorted(self.raw_data['SimTime'].unique())
        
        # Calculate sampling interval (difference between consecutive timestamps)
        if len(timestamps) > 1:
            sampling_interval_ns = timestamps[1] - timestamps[0]
        else:
            # Single timestamp - use the timestamp value itself as the interval
            sampling_interval_ns = timestamps[0]
        
        # Build accumulated demand matrices for each timestamp
        accumulated_matrices = []
        for ts in timestamps:
            data_at_ts = self.raw_data[self.raw_data['SimTime'] == ts]
            
            # Initialize matrix
            matrix = np.zeros((self.num_EPs, self.num_EPs))
            
            # Fill matrix with accumulated bytes from Sum.u64
            for _, row in data_at_ts.iterrows():
                src = row['src_id']
                dst = row['dst_id']
                bytes_sent = row['Sum.u64']
                matrix[src, dst] = bytes_sent
            
            accumulated_matrices.append((ts, matrix))
        
        # Convert to per-interval or keep accumulated based on use_per_interval flag
        if self.use_per_interval and len(accumulated_matrices) > 1:
            # Compute differences between consecutive accumulated matrices
            per_interval_matrices = []
            
            # First interval: use the first accumulated matrix as-is
            ts0, acc_matrix0 = accumulated_matrices[0]
            interval_bytes = acc_matrix0.copy()
            interval_gbps = (interval_bytes * 8) / sampling_interval_ns
            per_interval_matrices.append((ts0, interval_gbps))
            
            # Subsequent intervals: difference from previous
            for i in range(1, len(accumulated_matrices)):
                ts_curr, acc_matrix_curr = accumulated_matrices[i]
                ts_prev, acc_matrix_prev = accumulated_matrices[i-1]
                
                # Compute bytes sent in this interval
                interval_bytes = acc_matrix_curr - acc_matrix_prev
                
                # Convert to Gbps
                interval_gbps = (interval_bytes * 8) / sampling_interval_ns
                per_interval_matrices.append((ts_curr, interval_gbps))
            
            matrices = per_interval_matrices
        else:
            # Use accumulated matrices, convert to Gbps
            matrices = []
            for ts, acc_matrix in accumulated_matrices:
                gbps_matrix = (acc_matrix * 8) / sampling_interval_ns
                matrices.append((ts, gbps_matrix))
        
        return sampling_interval_ns, matrices
    
    def get_ave_message_lat_us(self):
        """
        Get average message latency in microseconds.
        Note: This metric is not directly available from aggregated statistics.
        Returns None for compatibility with the old API.
        """
        print("Warning: Average message latency not available from aggregated demand matrix data")
        return None
    
    def sample_traffic(self, num_samples: int, filtering_threshold: float = 0.0, auto_scale: bool = False):
        """
        Sample traffic demand matrices from the aggregated data.
        
        Args:
            num_samples: Number of samples to generate (can be any positive integer)
            filtering_threshold: Minimum max link load threshold for filtering
            auto_scale: Whether to auto-scale the matrices
            
        Returns:
            tuple: (matrices, weights, sampling_interval_us) or 
                   (matrices, weights, sampling_interval_us, scaling_factor) if auto_scale=True
        """
        total_matrices = len(self.demand_matrices)
        
        # Handle edge cases
        if num_samples <= 0:
            raise ValueError(f"num_samples must be positive, got {num_samples}")
        
        if num_samples > total_matrices:
            raise ValueError(f"num_samples is larger than the collect samples.")
            # print(f"Warning: num_samples ({num_samples}) > total_matrices ({total_matrices}). "
            #       f"Using {total_matrices} samples instead.")
            # num_samples = total_matrices
        
        # Calculate aggregation factor (round up to ensure we use all matrices)
        import math
        agg_factor = math.ceil(total_matrices / num_samples)
        
        # Aggregate matrices
        matrices = []
        for i in range(num_samples):
            # Sum matrices in this group
            start_idx = i * agg_factor
            end_idx = min(start_idx + agg_factor, total_matrices)  # Don't go past the end
            
            # Skip if we've exhausted all matrices
            if start_idx >= total_matrices:
                break
            
            aggregated_matrix = np.zeros((self.num_EPs, self.num_EPs))
            count = 0
            for j in range(start_idx, end_idx):
                _, matrix = self.demand_matrices[j]
                aggregated_matrix += matrix
                count += 1
            
            # Average the aggregated matrix to maintain Gbps units
            aggregated_matrix /= count
            matrices.append(aggregated_matrix)
        
        # Calculate effective interval (use average across all groups)
        avg_group_size = total_matrices / len(matrices)
        new_interval_ns = self.original_interval_ns * avg_group_size
        
        # All samples have equal weight since we're uniformly sampling
        weights = [1.0 / len(matrices)] * len(matrices)
        
        # Apply filtering and scaling
        filtered_matrices, filtered_weights = self.filter_traffic_demand_matrices(
            matrices, weights, filtering_threshold
        )
        
        sampling_interval_us = new_interval_ns / 1000  # Convert ns to us
        
        print(f"Sampled {len(matrices)} demand matrices from {total_matrices} total matrices")
        print(f"Average aggregation factor: {avg_group_size:.2f}, effective interval: {sampling_interval_us:.2f} us")
        
        if auto_scale:
            filtered_matrices, scaling_factor = self.auto_scale(filtered_matrices)
            return filtered_matrices, filtered_weights, sampling_interval_us, scaling_factor
        else:
            return filtered_matrices, filtered_weights, sampling_interval_us
    
    def filter_traffic_demand_matrices(self, input_matrices: list, input_weights: list, 
                                      max_link_load_threshold: float = 1.0):
        """
        Filter demand matrices based on maximum link load threshold.
        
        Args:
            input_matrices: List of demand matrices
            input_weights: List of weights for each matrix
            max_link_load_threshold: Minimum max link load to keep a matrix
            
        Returns:
            tuple: (filtered_matrices, filtered_weights)
        """
        if max_link_load_threshold <= 0.0:
            return input_matrices, input_weights
        
        # Import topology module
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
        from topoResearch.topologies.HPC_topo import HPC_topo
        
        _network = HPC_topo.initialize_child_instance(self.topo_name, self.V, self.D)
        _network.pre_calculate_ECMP_ASP()
        
        remaining_matrices = []
        remaining_weights = []
        
        for matrix_id, input_matrix in enumerate(input_matrices):
            core_link_flows, access_link_flows = _network.distribute_M_EPs_on_weighted_paths(
                _network.ECMP_ASP, self.EPR, input_matrix
            )
            max_link_load = max(
                max(core_link_flows) / self.Cap_core,
                max(access_link_flows) / self.Cap_access
            )
            
            if max_link_load >= max_link_load_threshold:
                remaining_matrices.append(input_matrix)
                remaining_weights.append(input_weights[matrix_id])
        
        # Normalize weights
        total_weight = sum(remaining_weights)
        if total_weight > 0:
            normalized_weights = [weight / total_weight for weight in remaining_weights]
        else:
            normalized_weights = []
        
        print(f"{len(input_matrices)} incoming matrices, {len(remaining_matrices)} left after filtering")
        
        return remaining_matrices, normalized_weights
    
    def auto_scale(self, input_matrices: list):
        """
        Auto-scale demand matrices to achieve an average max link load of 10.
        
        Args:
            input_matrices: List of demand matrices
            
        Returns:
            tuple: (scaled_matrices, scaling_factor)
        """
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
        from topoResearch.topologies.HPC_topo import HPC_topo
        
        _network = HPC_topo.initialize_child_instance(self.topo_name, self.V, self.D)
        _network.pre_calculate_ECMP_ASP()
        
        max_link_loads = []
        for input_matrix in input_matrices:
            core_link_flows, access_link_flows = _network.distribute_M_EPs_on_weighted_paths(
                _network.ECMP_ASP, self.EPR, input_matrix
            )
            max_link_load = max(
                max(core_link_flows) / self.Cap_core,
                max(access_link_flows) / self.Cap_access
            )
            max_link_loads.append(max_link_load)
        
        ave_max_link_load = np.average(max_link_loads)
        scaling_factor = 10 / ave_max_link_load
        print(f"auto scaling demand matrices, scaling factor = {scaling_factor}")
        
        scaled_matrices = [matrix * scaling_factor for matrix in input_matrices]
        return scaled_matrices, scaling_factor
    
    def get_accumulated_demand_matrix(self, plot: bool = False):
        """
        Get the accumulated demand matrix over all time periods.
        
        Args:
            plot: Whether to plot the matrix
            
        Returns:
            numpy.ndarray: Accumulated demand matrix (averaged over time in Gbps)
        """
        # Sum all matrices to get total
        accumulated = np.zeros((self.num_EPs, self.num_EPs))
        for _, matrix in self.demand_matrices:
            accumulated += matrix
        
        # Average to get mean Gbps over the entire period
        accumulated /= len(self.demand_matrices)
        
        if plot:
            fig, ax = plt.subplots(figsize=(8, 8))
            m_figure = ax.matshow(accumulated, vmin=0, vmax=np.max(accumulated))
            title_type = "average per-interval" if self.use_per_interval else "accumulated"
            ax.set_title(f'{self.topo_full_name}_{self.suffix}_{self.params["BENCH"]}: {title_type} demand matrix (Gbps)')
            plt.colorbar(m_figure)
            ax.set_xlabel("dest")
            ax.set_ylabel("src")
            plt.show()
        
        return accumulated
    
    def visualize_demand_evolution(self, vmax=None):
        """
        Create an animation showing how the demand matrix evolves over time.
        
        Args:
            vmax: Maximum value for colormap scale (auto-detected if None)
            
        Returns:
            Animation object
        """
        if vmax is None:
            vmax = max(np.max(matrix) for _, matrix in self.demand_matrices)
        
        def update_heatmap(frame):
            timestamp, matrix = self.demand_matrices[frame]
            m_figure.set_array(matrix)
            ax.set_title(f'Time: {timestamp / 1000:.1f} us, Unit: Gbps')
        
        # Initial empty matrix
        initial_matrix = np.zeros((self.num_EPs, self.num_EPs))
        fig, ax = plt.subplots(figsize=(8, 8))
        m_figure = ax.matshow(initial_matrix, vmin=0, vmax=vmax)
        ax.set_title('Time: 0.0 us')
        plt.colorbar(m_figure)
        
        ani = animation.FuncAnimation(fig, update_heatmap, frames=len(self.demand_matrices))
        title_type = "per-interval" if self.use_per_interval else "accumulated"
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}_{self.params["BENCH"]}: {title_type} demand matrix evolution')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        
        return ani
    
    def get_statistics(self):
        """
        Get statistics about the demand matrices.
        
        Returns:
            dict: Dictionary containing various statistics
        """
        total_traffic = []
        max_flows = []
        sparsity = []
        
        for _, matrix in self.demand_matrices:
            total_traffic.append(np.sum(matrix))
            max_flows.append(np.max(matrix))
            # Sparsity: fraction of zero entries
            sparsity.append(np.sum(matrix == 0) / (self.num_EPs ** 2))
        
        return {
            'num_matrices': len(self.demand_matrices),
            'sampling_interval_ns': self.original_interval_ns,
            'sampling_interval_us': self.original_interval_ns / 1000,
            'total_traffic_gbps': {
                'mean': np.mean(total_traffic),
                'std': np.std(total_traffic),
                'min': np.min(total_traffic),
                'max': np.max(total_traffic)
            },
            'max_flow_gbps': {
                'mean': np.mean(max_flows),
                'std': np.std(max_flows),
                'min': np.min(max_flows),
                'max': np.max(max_flows)
            },
            'sparsity': {
                'mean': np.mean(sparsity),
                'std': np.std(sparsity),
                'min': np.min(sparsity),
                'max': np.max(sparsity)
            }
        }
    
    def print_statistics(self):
        """Print statistics in a human-readable format."""
        stats = self.get_statistics()
        
        mode_str = "per-interval" if self.use_per_interval else "accumulated"
        print(f"\n{'='*60}")
        print(f"Demand Matrix Statistics ({mode_str} mode): {self.topo_full_name}")
        print(f"{'='*60}")
        print(f"Number of time samples: {stats['num_matrices']}")
        print(f"Sampling interval: {stats['sampling_interval_us']:.2f} us ({stats['sampling_interval_ns']} ns)")
        print(f"\nTotal Traffic (Gbps):")
        print(f"  Mean: {stats['total_traffic_gbps']['mean']:.2f}")
        print(f"  Std:  {stats['total_traffic_gbps']['std']:.2f}")
        print(f"  Min:  {stats['total_traffic_gbps']['min']:.2f}")
        print(f"  Max:  {stats['total_traffic_gbps']['max']:.2f}")
        print(f"\nMax Flow (Gbps):")
        print(f"  Mean: {stats['max_flow_gbps']['mean']:.4f}")
        print(f"  Std:  {stats['max_flow_gbps']['std']:.4f}")
        print(f"  Min:  {stats['max_flow_gbps']['min']:.4f}")
        print(f"  Max:  {stats['max_flow_gbps']['max']:.4f}")
        print(f"\nMatrix Sparsity (fraction of zeros):")
        print(f"  Mean: {stats['sparsity']['mean']:.4f}")
        print(f"  Std:  {stats['sparsity']['std']:.4f}")
        print(f"  Min:  {stats['sparsity']['min']:.4f}")
        print(f"  Max:  {stats['sparsity']['max']:.4f}")
        print(f"{'='*60}\n")
