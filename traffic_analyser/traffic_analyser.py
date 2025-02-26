import pandas as pd
import numpy as np
from IPython.core.display import display, HTML
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from .helpers import *
import sys

def diff_matrices(m1: np.ndarray, m2: np.ndarray) -> float:
    # Ensure matrices have the same shape
    if m1.shape != m2.shape:
        raise ValueError("Matrices must have the same shape.")
    # Calculate the sum of absolute differences
    return np.sum(np.abs(m1 - m2))

class traffic_analyser():
    def __init__(self, input_csv_path, V, D, topo_name, EPR, Cap_core, Cap_access, suffix, processing_method = 2):
        self.num_EPs=V*EPR
        self.topo_name=topo_name
        self.V = V
        self.D = D
        self.EPR=EPR
        self.Cap_core = Cap_core
        self.Cap_access = Cap_access
        self.topo_full_name=f"({V}, {D})_{topo_name}_{EPR}_EPR"
        self.suffix=suffix
        self.events=pd.read_csv(input_csv_path)
        self.max_time=self.events["time_ns"].max()
        self.min_time=self.events["time_ns"].min()
        self.pkt_data=self.process_data(processing_method)

        format_string = "traffic_BENCH_{BENCH}_EPR_{EPR}_ROUTING_{ROUTING}_V_{V}_D_{D}_TOPO_{TOPO}_SUFFIX_{SUFFIX}_.csv"
        self.params = extract_placeholders(format_string, input_csv_path)

        
    def process_data(self, _method):
        # Initialize an empty DataFrame to store the summarized data
        num_pkts = self.events["pkt_id"].max() + 1
        if _method == 1:
            # Method 1: Iterate over packet IDs, find in-network and out-network events
            new_data = pd.DataFrame(columns=['srcNIC', 'destNIC', 'Size_Bytes', 'pkt_id', 'enter_time', 'leave_time'])
            for pkt_id in range(num_pkts):
                pkt_events = self.events[self.events['pkt_id'] == pkt_id]
                assert(len(pkt_events.index) == 2)
                pkt_in_event = pkt_events[pkt_events['type'] == 'in']
                pkt_out_event = pkt_events[pkt_events['type'] == 'out']
                pkt_in_time = pkt_in_event['time_ns']
                pkt_out_time = pkt_out_event['time_ns']
                pkt_src = pkt_in_event['srcNIC']
                assert(pkt_src.values == pkt_out_event['srcNIC'].values)
                pkt_dest = pkt_in_event['destNIC']
                assert(pkt_dest.values == pkt_out_event['destNIC'].values)
                pkt_size = pkt_in_event['Size_Bytes']
                assert(pkt_size.values == pkt_out_event['Size_Bytes'].values)
                # Append the summarized data to the summary DataFrame
                new_data = pd.concat([new_data, pd.DataFrame([{
                    'srcNIC': pkt_src.values[0],
                    'destNIC': pkt_dest.values[0],
                    'Size_Bytes': pkt_size.values[0],
                    'pkt_id': pkt_id,
                    'enter_time': pkt_in_time.values[0],
                    'leave_time': pkt_out_time.values[0]
                }])], ignore_index=True)

            return new_data
        elif _method == 2:
            # Method 2: Iterate over all events, filling in cells based on type
            new_data = pd.DataFrame({
                'srcNIC': [-1] * num_pkts,
                'destNIC': [-1] * num_pkts,
                'Size_Bytes': [0] * num_pkts,
                'pkt_id': range(num_pkts),
                'enter_time': [0] * num_pkts,
                'leave_time': [0] * num_pkts
            })

            # Iterate over each event
            for _, event in self.events.iterrows():
                pkt_id = event['pkt_id']
                if event['type'] == 'in':
                    # Fill in the 'in' event details
                    new_data.at[pkt_id, 'srcNIC'] = event['srcNIC']
                    new_data.at[pkt_id, 'destNIC'] = event['destNIC']
                    new_data.at[pkt_id, 'Size_Bytes'] = event['Size_Bytes']
                    new_data.at[pkt_id, 'enter_time'] = event['time_ns']
                elif event['type'] == 'out':
                    # Check consistency with 'in' event details
                    assert new_data.at[pkt_id, 'srcNIC'] == event['srcNIC']
                    assert new_data.at[pkt_id, 'destNIC'] == event['destNIC']
                    assert new_data.at[pkt_id, 'Size_Bytes'] == event['Size_Bytes']
                    # Ensure leave_time is later than enter_time
                    assert event['time_ns'] > new_data.at[pkt_id, 'enter_time']
                    new_data.at[pkt_id, 'leave_time'] = event['time_ns']

            return new_data
        else:
            assert(0, "input arg '_method' is either 1 or 2")

    def get_ave_message_lat_us(self):
        # Calculate latencies for each packet
        latencies = self.pkt_data['leave_time'] - self.pkt_data['enter_time']
        # Handle any invalid (negative) latencies, if needed
        if (latencies < 0).any():
            raise ValueError("Some packets have negative latency. Check the 'enter_time' and 'leave_time' data.")
        # Calculate and return the average latency
        return latencies.mean()/1_000 # ns to us

    def sample_traffic(self, num_samples: int, filtering_threshold:float = 0.0, auto_scale:bool = False):
        # if method == "Enroute":
        #     print("invalid method for sampling traffic: ", method, "this method is disabled for now")
        #     sys.exit(1)
        #     # return self.sample_enroute_traffic(num_samples)
        # elif method == "Sent":
        matrices, weights, sampling_interval_us = self.sample_ranged_sent_traffic(num_samples)
        filtered_matrices, filtered_weights = self.filter_traffic_demand_matrices(matrices, weights, filtering_threshold)
        if auto_scale: 
            filtered_matrices, scaling_factor = self.auto_scale(filtered_matrices)
            return filtered_matrices, filtered_weights, sampling_interval_us, scaling_factor
        else:
            return filtered_matrices, filtered_weights, sampling_interval_us


    # This method of sampling (enroute) is questionable, because the unit would be Btyes, instead of Mbps for traffic demand matrices.
    # def sample_enroute_traffic(self, num_samples: int):
    #     # evenly sample the enroute traffic demand matrices in the traffic traces
    #     # return a list of traffic demand matrices with equal weights
    #     # sample points exclude the start and end time stamps

    #     # number of samples must be greater than one
    #     assert(num_samples>1)
    #     sampling_interval= (self.max_time-self.min_time)/(num_samples+1)
    #     matrices = []
    #     counts = []
    #     num_zeros = 0
    #     for sample in range(num_samples):
    #         current_time =  self.min_time + (1+sample)*sampling_interval
    #         sampled_matrix = np.zeros((self.num_nics, self.num_nics))
    #         sampled_packets = self.pkt_data[(self.pkt_data['enter_time'] <= current_time) & (current_time <= self.pkt_data['leave_time'])]
    #         # Update sampled_matrix based on in-network packets
    #         for _, row in sampled_packets.iterrows():
    #             src_nic = row['srcNIC']
    #             dest_nic = row['destNIC']
    #             sampled_matrix[src_nic][dest_nic] += row['Size_Bytes']

    #         # skip empty matrices:
    #         if np.sum(sampled_matrix) == 0:
    #             num_zeros+=1
    #             continue

    #         Degenerate = False
    #         for loc, previous_m in enumerate(matrices):
    #             if diff_matrices(previous_m, sampled_matrix) < 0.1:
    #                 counts[loc] += 1
    #                 Degenerate = True
    #                 break
    #         if not Degenerate:
    #             matrices.append(sampled_matrix)
    #             counts.append(1)

    #     assert(num_samples == sum(counts)+num_zeros)
    #     weights = [count/sum(counts) for count in counts]
    #     return matrices, weights
        

    def sample_ranged_sent_traffic(self, num_samples: int):
        # evenly divide the benchmark time span into pieceds, and then calculate the accumulated traffic demand matrices in each period of time
        # return a list of traffic demand matrices with equal weights

        # sample points exclude the start time stamp, but include the end time stamp

        # number of samples must be greater than one
        assert(num_samples>=1)
        sampling_interval:float=(self.max_time-self.min_time)/num_samples # unit: nanosecond
        
        # sample the traffic traces with the sampling interval, the sampling interval has unit of millisecond
        # if the packet size is 45 B and link bandwidth is 16Gbps, then forwarding one packet need 23 ns.
        # The sampling interval should be big enough to neglect the forwarding of an individual packets, otherwise the sampled traffic demand matrix will have very large entries, which is not realistic
        # therefore, sampling_interval in this case is at least 1 microsecond
        # if sampling_interval < 1000:

        matrices = []
        counts = []
        num_zeros = 0
        for sample in range(num_samples):
            current_time =  self.min_time + sample*sampling_interval
            next_time = current_time + sampling_interval
            sampled_matrix = np.zeros((self.num_EPs, self.num_EPs))
            sampled_packets = self.pkt_data[(self.pkt_data['enter_time'] < next_time) & (self.pkt_data['enter_time'] >= current_time)]
            for _, row in sampled_packets.iterrows():
                src_nic = row['srcNIC']
                dest_nic = row['destNIC']
                sampled_matrix[src_nic][dest_nic] += 8*row['Size_Bytes']/sampling_interval #Gbps

            # skip empty matrices:
            if np.sum(sampled_matrix) == 0:
                num_zeros += 1
                continue

            Degenerate = False
            for loc, previous_m in enumerate(matrices):
                if diff_matrices(previous_m, sampled_matrix) < 0.1:
                    counts[loc] += 1
                    Degenerate = True
                    break
            if not Degenerate:
                matrices.append(sampled_matrix)
                counts.append(1)

        assert(num_samples == sum(counts)+num_zeros)
        weights = [count/sum(counts) for count in counts]
        return matrices, weights, sampling_interval/1_000 # return matrices, the weights and the sampling interval in microseconds

    def filter_traffic_demand_matrices(self, input_matrices:list, input_weights:list, max_link_load_threshold:float = 1.0):
        # take the sampled demand matrices as input, return filtered demand matrices
        # for each of the traffic demand matrix, we do a flow-level modeling, if the max (core/access) link load is lower than the threshold value, discard that traffic demand matrix.
        
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
        from topoResearch.topologies.HPC_topo import HPC_topo
        import topoResearch.global_helpers as gl
        _network = HPC_topo.initialize_child_instance(self.topo_name, self.V, self.D)
        _network.pre_calculate_ECMP_ASP()
        
        # List to store indices of matrices to keep
        remaining_matrices = []
        remaining_weights = []
        # Iterate over all matrices and filter based on the max link load
        for matrix_id, input_matrix in enumerate(input_matrices):
            core_link_flows, access_link_flows = _network.distribute_M_EPs_on_weighted_paths(_network.ECMP_ASP, self.EPR, input_matrix)
            max_link_load = max(max(core_link_flows) / self.Cap_core, max(access_link_flows) / self.Cap_access)
            if max_link_load >= max_link_load_threshold:
                remaining_matrices.append(input_matrix)
                remaining_weights.append(input_weights[matrix_id])
        # Normalize weights while preserving their original ratio
        total_weight = sum(remaining_weights)
        if total_weight > 0:
            normalized_weights = [weight / total_weight for weight in remaining_weights]
        else:
            normalized_weights = []

        print(f"{len(input_matrices)} incoming matrices, {len(remaining_matrices)} left after filtering")

        return remaining_matrices, normalized_weights


    def auto_scale(self, input_matrices:list):
        # take the sampled demand matrices as input, return scaled demand matrices
        # for each of the traffic demand matrix, we do a flow-level modeling, if the max (core/access) link load is lower than the threshold value, discard that traffic demand matrix.
        # calculate the max_link_load for each matrix, and then scale them all together so that the average max_link_load = 10
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
        from topoResearch.topologies.HPC_topo import HPC_topo
        import topoResearch.global_helpers as gl
        _network = HPC_topo.initialize_child_instance(self.topo_name, self.V, self.D)
        _network.pre_calculate_ECMP_ASP()
        
        max_link_loads = []
        for input_matrix in input_matrices:
            core_link_flows, access_link_flows = _network.distribute_M_EPs_on_weighted_paths(_network.ECMP_ASP, self.EPR, input_matrix)
            max_link_load = max(max(core_link_flows) / self.Cap_core, max(access_link_flows) / self.Cap_access)
            max_link_loads.append(max_link_load)

        ave_max_link_load = np.average(max_link_loads)
        scaling_factor = 10/ave_max_link_load
        print(f"auto scaling demand matrices, scaling factor = {scaling_factor}")

        scaled_matrices = [matrix*scaling_factor for matrix in input_matrices]
        return scaled_matrices, scaling_factor

    def get_accumulated_demand_matrix(self, plot: bool = False):
        demand_matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
        for _, row in self.pkt_data.iterrows():
            src_nic = row['srcNIC']
            dest_nic = row['destNIC']
            demand_matrix[src_nic][dest_nic] += row['Size_Bytes']
        if plot:
            fig, ax = plt.subplots(figsize=(8,8))
            m_figure = ax.matshow(demand_matrix, vmin=0, vmax=np.max(demand_matrix))
            ax.set_title(f'{self.topo_full_name}_{self.suffix}_{self.params["BENCH"]}: accumulated demand matrix')
            plt.colorbar(m_figure)
            ax.set_xlabel("dest")
            ax.set_ylabel("src")
            plt.show()
        return demand_matrix

    def visualize_enroute_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int((self.max_time-self.min_time)/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int((self.max_time-self.min_time)/sampling_interval)+1
        def update_heatmap(frame):
            packet_matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
            current_time=0
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                in_network_packets = self.pkt_data[(self.pkt_data['enter_time'] <= current_time) & (current_time <= self.pkt_data['leave_time'])]
                # Update packet_matrix based on in-network packets
                for _, row in in_network_packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'time stamp: {current_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 us' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames+1)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}_{self.params["BENCH"]}: en-route')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani
    
    def visualize_accumulated_sent_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int((self.max_time-self.min_time)/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int((self.max_time-self.min_time)/sampling_interval)+1
        def update_heatmap(frame):
            packet_matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
            current_time=0
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                _packets = self.pkt_data[(self.pkt_data['enter_time'] <= current_time)]
                # Update packet_matrix based on in-network packets
                for _, row in _packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'time stamp: {current_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 us' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames+1)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}_{self.params["BENCH"]}: accumulated sent')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani
    
    def visualize_ranged_enroute_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int((self.max_time-self.min_time)/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int((self.max_time-self.min_time)/sampling_interval)+1
        def update_heatmap(frame):
            packet_matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
            current_time=0
            next_time=self.min_time
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                next_time=self.min_time + (frame+1)*sampling_interval
                in_network_packets = self.pkt_data[(self.pkt_data['enter_time'] <= next_time) & (self.pkt_data['leave_time'] >= current_time)]
                # Update packet_matrix based on in-network packets
                for _, row in in_network_packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'from {current_time/1000} us to {next_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 us' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames+1)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}_{self.params["BENCH"]}: ranged en-route')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani
    
    def visualize_ranged_sent_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int((self.max_time-self.min_time)/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int((self.max_time-self.min_time)/sampling_interval)+1
        def update_heatmap(frame):
            packet_matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
            current_time=0
            next_time=self.min_time
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                next_time=self.min_time + (frame+1)*sampling_interval
                _packets = self.pkt_data[(self.pkt_data['enter_time'] <= next_time) & (self.pkt_data['enter_time'] >= current_time)]
                # Update packet_matrix based on in-network packets
                for _, row in _packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
                
            m_figure.set_array(packet_matrix)
            ax.set_title(f'from {current_time/1000} us to {next_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_EPs)] for _ in range(self.num_EPs)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 us' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames+1)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}_{self.params["BENCH"]}: ranged sent')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani