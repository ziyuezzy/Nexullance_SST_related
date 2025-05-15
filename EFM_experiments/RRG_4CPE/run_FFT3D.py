from EFM_experiments.wrappers import run_EFM, MD_Nexu_sweeper
import csv

bench = "FFT3D"
benchargs:str=f" nx=ny=nz npRow=12" # temp usage for file names

default_config_dict = {
    'UNIFIED_ROUTER_LINK_BW':16,  #Gbps
    'V':36,
    'D':5,
    'topo_name':"RRG",
    # 'paths':"ASP",
    'identifier':"ASP",
    # 'routing_algo': "ugal_precise",
    'routing_algo': "", # same for two subnets
    'benchmark': "",
    'benchargs': "",
    'Cores_per_EP': 4
}

# Specify the output CSV file name
csv_files = {"ECMP_ASP":f"{bench}{benchargs}_ECMP_ASP_result.csv",
             "ugal":f"{bench}{benchargs}_ugal_result.csv",
            #  "ugal_threshold":f"{bench}{benchargs}_ugal_threshold_result.csv",
             "MD_IT":f"{bench}{benchargs}_MD_IT_result.csv",
             "MD_MP_APST4":f"{bench}{benchargs}_MD_MP_APST4_result.csv"}

def write_into_csvfile(filename:csv, content_row:list):
    with open(filename, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(content_row)
        csv_file.flush()

write_into_csvfile(csv_files["ECMP_ASP"], ["nx", "benchtime[us]", "speedup"]) # TODO: measure the actual phi via simulation, compare with the flow-modeling results
write_into_csvfile(csv_files["ugal"], ["nx", "benchtime[us]", "speedup"])
# write_into_csvfile(csv_files["ugal_threshold"], ["nx", "benchtime[us]", "speedup"])
write_into_csvfile(csv_files["MD_IT"], ["nx", "samples", "sampling_interval_us", "ave_message_lat_us", "traffic_scaling_factor", "predicted_obj_func_ECMP_ASP", "predicted_obj_func_MD_IT", "benchtime[us]", "speedup"])
write_into_csvfile(csv_files["MD_MP_APST4"], ["nx", "samples", "sampling_interval_us", "ave_message_lat_us", "traffic_scaling_factor", "predicted_obj_func_ECMP_ASP", "predicted_obj_func_MD_MP_APST4", "benchtime[us]", "speedup"])

# for problem_size in [100]:
for problem_size in [256, 512, 1024, 2048]:
    bench = "FFT3D"
    benchargs:str=f" nx={problem_size} ny={problem_size} nz={problem_size} npRow=12"

    # Write the data rows
    ECMP_ASP_time = run_EFM(bench, benchargs, default_config_dict=default_config_dict)
    write_into_csvfile(csv_files["ECMP_ASP"], [problem_size, ECMP_ASP_time, 1])

    ugal_time = run_EFM(bench, benchargs, routing="ugal_precise", default_config_dict=default_config_dict)
    write_into_csvfile(csv_files["ugal"], [problem_size, ugal_time, ECMP_ASP_time/ugal_time])

    # ugal_time = run_EFM(bench, benchargs, routing="ugal_threshold")
    # write_into_csvfile(csv_files["ugal_threshold"], [problem_size, ugal_time, ECMP_ASP_time/ugal_time])

    num_samples_sweep = [1, 2, 4, 8, 16, 32, 64, 128]
    
    exp_container = MD_Nexu_sweeper(bench, benchargs, default_config_dict=default_config_dict)

    MD_IT_result = exp_container.sweep_samples(num_samples_sweep, "IT", auto_scaling=True)
    for i, num_samples in enumerate(num_samples_sweep):
        write_into_csvfile(csv_files["MD_IT"], 
            [problem_size, num_samples, MD_IT_result["sampling_interval_us"][i], MD_IT_result["ave_message_lat_us"],
             MD_IT_result["scaling_factor"][i], MD_IT_result["obj_func_ECMP_ASP"][i], 
                MD_IT_result["obj_func_MD"][i], MD_IT_result["benchtime[us]"][i], ECMP_ASP_time/MD_IT_result["benchtime[us]"][i]])

    MD_MP_result = exp_container.sweep_samples(num_samples_sweep, "MP_APST_4", auto_scaling=True)
    for i, num_samples in enumerate(num_samples_sweep):
        write_into_csvfile(csv_files["MD_MP_APST4"], 
            [problem_size, num_samples, MD_MP_result["sampling_interval_us"][i], MD_IT_result["ave_message_lat_us"], 
             MD_MP_result["scaling_factor"][i], MD_MP_result["obj_func_ECMP_ASP"][i], 
                MD_MP_result["obj_func_MD"][i], MD_MP_result["benchtime[us]"][i], ECMP_ASP_time/MD_MP_result["benchtime[us]"][i]])

    # MD_MP_result = sweep_MD_Nexu_samples(bench, benchargs, num_samples_sweep, "MP_APST_4")
    # for samples, result in MD_MP.items():
    #     writer.writerow([f"MD_Nexu_MP_APST_4_with_{samples}EnrouteSamples", result, ECMP_ASP_time/result])
    # print(f"Data has been written to {csv_filename}")
