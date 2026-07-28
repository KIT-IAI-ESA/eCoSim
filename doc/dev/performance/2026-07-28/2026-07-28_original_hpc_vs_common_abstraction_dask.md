# Original HPC vs Common Abstraction Performance

## DASK
### test_client_server_batch_steps

#### happy path
<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 925ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.021s (= 0.021s total)
## Simulation execution time: 0h 0m 0.567s (= 0.567s total)
## Simulation stop time: 0h 0m 0.026s (= 0.026s total)
## Server uptime: None
####################################
</td>
</tr>
</table>

#### with empty repository
<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 867ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.023s (= 0.023s total)
## Simulation execution time: 0h 0m 0.578s (= 0.578s total)
## Simulation stop time: 0h 0m 0.024s (= 0.024s total)
## Server uptime: None
####################################
</td>
</tr>
</table>

#### different completed steps step4 step5
<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 897ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.022s (= 0.022s total)
## Simulation execution time: 0h 0m 0.567s (= 0.567s total)
## Simulation stop time: 0h 0m 0.022s (= 0.022s total)
## Server uptime: None
####################################
</td>
</tr>
</table>

#### different completed steps step1 step5
<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 903ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.020s (= 0.020s total)
## Simulation execution time: 0h 0m 0.576s (= 0.576s total)
## Simulation stop time: 0h 0m 0.023s (= 0.023s total)
## Server uptime: None
####################################
</td>
</tr>
</table>


### test_codependent_clients_server

<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 9s 472ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.027s (= 0.027s total)
## Simulation execution time: 0h 0m 8.173s (= 8.173s total)
## Simulation stop time: 0h 0m 0.032s (= 0.032s total)
## Server uptime: None
####################################
</td>
</tr>
</table>


### test_matrix_transfer

<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 6s 785ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.022s (= 0.022s total)
## Simulation execution time: 0h 0m 5.509s (= 5.509s total)
## Simulation stop time: 0h 0m 0.029s (= 0.029s total)
## Server uptime: None
####################################
</td>
</tr>
</table>


### test_single_client_server

<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 4s 86ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.020s (= 0.020s total)
## Simulation execution time: 0h 0m 2.940s (= 2.940s total)
## Simulation stop time: 0h 0m 0.019s (= 0.019s total)
## Server uptime: None
####################################
</td>
</tr>
</table>

### test_three_client_server

<table>
<tr>
<th>Original HPC</th>
<th>Common Abstraction</th>
</tr>
<tr>
<td>
</td>
<td>
Total test time: 1s 649ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.032s (= 0.032s total)
## Simulation execution time: 0h 0m 0.444s (= 0.444s total)
## Simulation stop time: 0h 0m 0.033s (= 0.033s total)
## Server uptime: None
####################################
</td>
</tr>
</table>
