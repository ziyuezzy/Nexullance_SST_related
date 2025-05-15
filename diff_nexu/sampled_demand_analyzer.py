import pickle
import numpy as np
import matplotlib.pyplot as plt
from topoResearch.global_helpers import convert_M_EPs_to_M_R

class sampled_demand_analyzer:
    def __init__(self, pickle_file: str):
        self.raw_data = pickle.load(open(pickle_file, "rb"))

        # the pickle file should contain the following
        # {
        # 'topo_name': topo_name,
        # 'V': V,
        # 'D': D,
        # 'EPR': EPR,
        # 'Cap_links': Cap_links,
        # 'benchmark': bench,
        # 'benchargs': benchargs,
        # 'traffic_trace_file': traffic_trace_file,
        # 'ave_latency[us]': analyser.get_ave_message_lat_us(),

        # 'matrices': [sampled_demand_matrices],
        # 'num_samples': [num_samples],
        # 'sample_interval': [sample_interval],
        # }

    def get_inter_switch_demand_matrices(self, num_samples: int = None, sample_interval: float = None):
        """
        Get the sampled demand matrices from the raw data, aggregate it for inter-switch traffic. 
        according to the specified num_samples and sample_interval (at least one should be provided).
        """
        # Find the index of the sampled demand matrices
        if num_samples is not None:
            index = self.raw_data['num_samples'].index(num_samples)
        elif sample_interval is not None:
            index = self.raw_data['sample_interval'].index(sample_interval)
        else:
            raise ValueError("Invalid num_samples or sample_interval provided.")
        
        result_matrices = []
        for matrix in self.raw_data['matrices'][index]:
            result_matrices.append(convert_M_EPs_to_M_R(matrix, self.raw_data['V'], self.raw_data['EPR']))

        return result_matrices, self.raw_data['num_samples'][index], self.raw_data['sample_interval'][index]

    def convert(self, num_samples: int = None, sample_interval: float = None):
        # Find the index of the sampled demand matrices
        if num_samples is not None:
            index = self.raw_data['num_samples'].index(num_samples)
        elif sample_interval is not None:
            index = self.raw_data['sample_interval'].index(sample_interval)
        else:
            raise ValueError("Invalid num_samples or sample_interval provided.")
        # Return the sampled demand matrices
        return self.raw_data['num_samples'][index], self.raw_data['sample_interval'][index]

    def illustrate_matrices(self, num_samples: int = None, sample_interval: float = None):
        import matplotlib.animation as animation

        traffic_matrices, num_samples, sample_interval = self.get_inter_switch_demand_matrices(num_samples, sample_interval)
        M=traffic_matrices[0]
        fig, ax = plt.subplots()
        matrice = ax.matshow(M, vmin=0, vmax=np.max(traffic_matrices))
        ax.set_xlabel(f'traffic at: 0 ' )
        plt.colorbar(matrice)

        def update(i):
            M=traffic_matrices[i]
            matrice.set_data(M)
            ax.set_xlabel(f'traffic at: {i*sample_interval} us' )

        ani = animation.FuncAnimation(fig, update, frames=len(traffic_matrices))
        return ani

    def plot_demand_and_diff(self, num_samples: int = None, sample_interval: float = None):
        # Get the difference demand matrices
        sum_demands = self.cal_sum_demand(num_samples=num_samples, sample_interval=sample_interval)
        diff_demand = self.cal_diff_demand(num_samples=num_samples, sample_interval=sample_interval)
        num_samples, sample_interval = self.convert(num_samples, sample_interval)

        x_series = np.arange(len(diff_demand))*sample_interval # [us]

        # Plot the difference demand matrices
        fig, ax = plt.subplots()
        ax.scatter(x_series, diff_demand, label="Differential Demand", c="red", alpha=0.5, marker='x')
        ax.scatter(x_series, sum_demands, label="Sum Demand", c="blue", alpha=0.5)
        ax.set_xlabel("Simulated Time [us]")
        ax.set_ylabel("Sum of absolute differences [Bytes]")
        ax.set_title(f"num_samples={num_samples}, sample_interval={round(sample_interval)} us")
        ax.legend()
        plt.show()
    
    def plot_diff_demand_compare_all(self):
        fig, ax = plt.subplots(figsize=(12, 6))  # Increased figure width
        for num_samples, sample_interval in zip(self.raw_data['num_samples'], self.raw_data['sample_interval']):
            if num_samples <= 2:
                continue
            # Get the difference demand matrices
            diff_demand = self.cal_diff_demand(sample_interval=sample_interval)
            x_series = np.arange(len(diff_demand))*sample_interval # [us]
            ax.scatter(x_series, diff_demand, label=f"{num_samples} samples", alpha=0.7)
        ax.set_xlabel("Simulated Time [us]")
        ax.set_ylabel("Sum of absolute differences [Bytes]")
        plt.subplots_adjust(right=0.85)  # Adjust right margin for legend
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_yscale('log')
        plt.show()

    def cal_mean_diff_demand(self, diff_method=None, num_samples: int = None, sample_interval: float = None) -> float:
        # Set default diff_method to elementwise_diff_sum if not provided
        if diff_method is None:
            diff_method = self.elementwise_diff_sum

        diff_demand = self.cal_diff_demand(diff_method, num_samples, sample_interval)
        # Calculate the mean of the differences
        mean_diff = sum(diff_demand) / len(diff_demand)
        return mean_diff

    def cal_diff_demand(self, diff_method=None, num_samples: int = None, sample_interval: float = None) -> list[float]:
        """
        for two demand matrices, the difference is evaluated by the diff_method with one float value
        Set default diff_method to elementwise_diff_sum if not provided
        """
        if diff_method is None:
            diff_method = self.elementwise_diff_sum

        matrices = self.get_inter_switch_demand_matrices(num_samples, sample_interval)[0]
        # Calculate the difference between the two adjacent demand matrices
        # and store the result in a new list
        diff_demand: list[float] = []
        diff_demand.append(0)
        # diff_demand.append(matrices[0].sum())
        for i in range(len(matrices) - 1):
            diff_demand.append(diff_method(matrices[i], matrices[i + 1]))
        return diff_demand
    
    def cal_sum_demand(self, num_samples: int = None, sample_interval: float = None) -> list[float]:
        matrices = self.get_inter_switch_demand_matrices(num_samples, sample_interval)[0]
        # Calculate the difference between the two adjacent demand matrices
        # and store the result in a new list
        diff_demand: list[float] = []
        for i in range(len(matrices)):
            diff_demand.append(matrices[i].sum())
        return diff_demand

    def elementwise_diff_sum(self, matrix_1, matrix_2) -> float:

        # for all-zero matrix, we now consider it as an outliner due to simulation artifact
        if matrix_1.sum() == 0 or matrix_2.sum() == 0:
            return 0.0
        
        # Calculate the element-wise difference between two matrices
        diff_matrix = abs(matrix_1 - matrix_2)
        diff_sum = diff_matrix.sum()
        return diff_sum
        
    def plot_violin_compare_all(self, scattering: bool = False):
        """
        Plot the violin plot using the 'cal_diff_demand' method, for all sample intervals,
        Each sampling interval corresponds to one violin, fixed at the x-axis.
        x-axis (bottom): sample_interval [us]
        secondary x-axis (top): num_samples
        y-axis: diff_demand [Gbps]
        """
        fig, ax = plt.subplots()
        positions = []
        data = []
        num_samples_list = []
        violin_widths = []
        
        # Collect data for violin plots
        for num_samples, sample_interval in zip(self.raw_data['num_samples'], self.raw_data['sample_interval']):
            if num_samples <= 2:
                continue
            diff_demand = self.cal_diff_demand(sample_interval=sample_interval)
            positions.append(sample_interval)
            data.append(diff_demand)
            violin_widths.append(1000/num_samples)
            
            num_samples_list.append(num_samples)
        
        # Create violin plot
        violin_parts = ax.violinplot(data, positions=positions, showmeans=True, widths=violin_widths)
        
        if scattering:
            # Add scatter plots
            for pos, series in zip(positions, data):
                # Generate small random x-offsets for better visualization
                x_jitter = np.random.normal(pos, 0.02*pos, size=len(series))
                ax.scatter(x_jitter, series, alpha=0.5, s=1)
        
        # Set up primary x-axis (sample interval)
        ax.set_xlabel("Sample interval [us]")
        ax.set_xscale('log')
        ax.set_ylabel("Sum of absolute differences [Bytes]")
        # ax.set_ylim(100)
        # ax.set_yscale('log')
        
        ax.invert_xaxis()

        # Secondary x-axis (top)
        ax2 = ax.twiny()  # Create a secondary x-axis
        ax2.set_xscale("log")
        ax2.set_xlim(ax.get_xlim())  # Sync the limits with the primary x-axis
        num_samples = num_samples_list
        ax2.set_xticks(positions)
        ax2.set_xticklabels(num_samples)
        ax2.set_xlabel("number of samples $\\nu$")