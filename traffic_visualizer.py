import pandas as pd
import numpy as np
from IPython.core.display import display, HTML
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from helpers import *

class traffic_visualizer():
    def __init__(self, input_csv_path, V, D, topo_name, EPR, suffix):
        self.num_nics=V*EPR
        self.topo_full_name=f"({V}, {D})_{topo_name}_{EPR}_EPR"
        self.suffix=suffix
        self.data=pd.read_csv(input_csv_path)
        self.max_time=self.data["time_ns"].max()
        self.min_time=self.data["time_ns"].min()
        self.data=self.process_data(self.data, self.num_nics)

        format_string = "traffic_BENCH_{BENCH}_EPR_{EPR}_ROUTING_{ROUTING}_V_{V}_D_{D}_TOPO_{TOPO}_SUFFIX_{SUFFIX}_.csv"
        self.params = extract_placeholders(format_string, input_csv_path)

        
    def process_data(self, _data, _num_nics):
        # Initialize an empty DataFrame to store the summarized data
        new_data = pd.DataFrame(columns=['srcNIC', 'destNIC', 'Size_Bytes', 'pkt_id', 'enter_time', 'leave_time'])
        num_pkts=_data["pkt_id"].max()+1

        for pkt_id in range(num_pkts):
            pkt_events=_data[_data['pkt_id']==pkt_id]
            assert(len(pkt_events.index)==2)
            pkt_in_event=pkt_events[pkt_events['type']=='in']
            pkt_out_event=pkt_events[pkt_events['type']=='out']
            pkt_in_time=pkt_in_event['time_ns']
            pkt_out_time=pkt_out_event['time_ns']
            pkt_src=pkt_in_event['srcNIC']
            assert(pkt_src.values==pkt_out_event['srcNIC'].values)
            pkt_dest=pkt_in_event['destNIC']
            assert(pkt_dest.values==pkt_out_event['destNIC'].values)
            pkt_size=pkt_in_event['Size_Bytes']
            assert(pkt_size.values==pkt_out_event['Size_Bytes'].values)
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
    
    def get_accumulated_demand_matrix(self, plot: bool = False):
        demand_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
        for _, row in self.data.iterrows():
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
            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            current_time=0
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                in_network_packets = self.data[(self.data['enter_time'] <= current_time) & (current_time <= self.data['leave_time'])]
                # Update packet_matrix based on in-network packets
                for _, row in in_network_packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'time stamp: {current_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
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
            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            current_time=0
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                _packets = self.data[(self.data['enter_time'] <= current_time)]
                # Update packet_matrix based on in-network packets
                for _, row in _packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'time stamp: {current_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
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
            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            current_time=0
            next_time=self.min_time
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                next_time=self.min_time + (frame+1)*sampling_interval
                in_network_packets = self.data[(self.data['enter_time'] <= next_time) & (self.data['leave_time'] >= current_time)]
                # Update packet_matrix based on in-network packets
                for _, row in in_network_packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
            
            m_figure.set_array(packet_matrix)
            ax.set_title(f'from {current_time/1000} us to {next_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
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
            packet_matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
            current_time=0
            next_time=self.min_time
            if frame>0: # ensure an empty start
                frame=frame-1
                current_time = self.min_time + frame*sampling_interval
                next_time=self.min_time + (frame+1)*sampling_interval
                _packets = self.data[(self.data['enter_time'] <= next_time) & (self.data['enter_time'] >= current_time)]
                # Update packet_matrix based on in-network packets
                for _, row in _packets.iterrows():
                    src_nic = row['srcNIC']
                    dest_nic = row['destNIC']
                    packet_matrix[src_nic][dest_nic] += row['Size_Bytes']
                
            m_figure.set_array(packet_matrix)
            ax.set_title(f'from {current_time/1000} us to {next_time/1000} us, unit: Bytes' )

        matrix = [[0 for _ in range(self.num_nics)] for _ in range(self.num_nics)]
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