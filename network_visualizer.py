import pandas as pd
import numpy as np
from IPython.core.display import display, HTML
import matplotlib.pyplot as plt
import matplotlib.animation as animation

class network_visualizer():
    def __init__(self, input_csv_path, V, D, topo_name, EPR, suffix):
        self.num_nics=V*EPR
        self.topo_full_name=f"({V}, {D})_{topo_name}_{EPR}_EPR"
        self.suffix=suffix
        self.data=pd.read_csv(input_csv_path)
        self.max_time=self.data["time_ns"].max()
        self.data=self.process_data(self.data, self.num_nics)
        
    def process_data(self, _data, _num_nics):
        # Initialize an empty DataFrame to store the summarized data
        new_data = pd.DataFrame(columns=['srcNIC', 'destNIC', 'Size_Bytes', 'pkt_id', 'enter_time', 'leave_time'])
        # Iterate through each unique source NIC
        for src_nic in range(_num_nics):
            # Filter rows where the source NIC is the current NIC
            src_rows = _data[_data['srcNIC'] == src_nic]
            # Iterate through each unique destination NIC for the source NIC
            for dest_nic in range(_num_nics):
                # Filter rows where the destination NIC is the current NIC
                dest_rows = src_rows[src_rows['destNIC'] == dest_nic]
                # Filter 'in' events for the current source-destination pair
                in_events = dest_rows[dest_rows['type'] == 'in']
                # Filter 'out' events for the current source-destination pair
                out_events = dest_rows[dest_rows['type'] == 'out']
                # Iterate through each 'in' event
                for _, in_event in in_events.iterrows():
                    enter_time = in_event['time_ns']
                    out_events[out_events['pkt_id'] == in_event['pkt_id']]
                    # assert(out_events.size()==1)
                    out_event = out_events.iloc[0]
                    assert(out_event is not None)
                    leave_time = out_event['time_ns']
                    size_bytes = in_event['Size_Bytes']
                    pkt_id = in_event['pkt_id']
                    # Append the summarized data to the summary DataFrame
                    new_data = pd.concat([new_data, pd.DataFrame([{
                        'srcNIC': src_nic,
                        'destNIC': dest_nic,
                        'Size_Bytes': size_bytes,
                        'pkt_id': pkt_id,
                        'enter_time': enter_time,
                        'leave_time': leave_time
                    }])], ignore_index=True)
        return new_data

    def visualize_enroute_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int(self.max_time/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int(self.max_time/sampling_interval)+1
        def update_heatmap(frame):
            current_time = frame*sampling_interval
            in_network_packets = self.data[(self.data['enter_time'] <= current_time) & (current_time <= self.data['leave_time'])]

            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            # Update packet_matrix based on in-network packets
            for _, row in in_network_packets.iterrows():
                src_nic = row['srcNIC']
                dest_nic = row['destNIC']
                packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'time stamp: {frame*sampling_interval} ns' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 ns' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}: en-route')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani
    
    def visualize_accumulated_sent_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int(self.max_time/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int(self.max_time/sampling_interval)+1

        def update_heatmap(frame):
            current_time = frame*sampling_interval
            in_network_packets = self.data[(self.data['enter_time'] <= current_time)]

            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            # Update packet_matrix based on in-network packets
            for _, row in in_network_packets.iterrows():
                src_nic = row['srcNIC']
                dest_nic = row['destNIC']
                packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'time stamp: {frame*sampling_interval} ns' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 ns' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}: acccumulated sent')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani
    
    def visualize_ranged_enroute_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int(self.max_time/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int(self.max_time/sampling_interval)+1

        def update_heatmap(frame):
            current_time = frame*sampling_interval
            next_time=(frame+1)*sampling_interval
            in_network_packets = self.data[(self.data['enter_time'] <= next_time) & (self.data['leave_time'] >= current_time)]

            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            # Update packet_matrix based on in-network packets
            for _, row in in_network_packets.iterrows():
                src_nic = row['srcNIC']
                dest_nic = row['destNIC']
                packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_xlabel(f'from {frame*sampling_interval} ns to {(frame+1)*sampling_interval} ns' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 ns' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}: ranged en-route')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani
    
    def visualize_ranged_sent_data(self, num_frames=0, sampling_interval=0, vmax=1000):
        if num_frames:
            sampling_interval=int(self.max_time/num_frames)
            num_frames=num_frames+1
        elif sampling_interval:
            num_frames=int(self.max_time/sampling_interval)+1

        def update_heatmap(frame):
            current_time = frame*sampling_interval
            next_time=(frame+1)*sampling_interval
            in_network_packets = self.data[(self.data['enter_time'] <= next_time) & (self.data['enter_time'] >= current_time)]

            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            # Update packet_matrix based on in-network packets
            for _, row in in_network_packets.iterrows():
                src_nic = row['srcNIC']
                dest_nic = row['destNIC']
                packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_xlabel(f'from {frame*sampling_interval} ns to {(frame+1)*sampling_interval} ns' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
        fig, ax = plt.subplots(figsize=(8,8))
        m_figure = ax.matshow(matrix, vmin=0, vmax=vmax) #TODO: max = buffer size?
        ax.set_title(f'time stamp: 0 ns' )
        plt.colorbar(m_figure) #TODO: delete this line?

        ani = animation.FuncAnimation(fig, update_heatmap, frames=num_frames)
        fig.suptitle(f'{self.topo_full_name}_{self.suffix}: ranged sent')
        ax.set_xlabel("dest")
        ax.set_ylabel("src")
        plt.close()
        return ani