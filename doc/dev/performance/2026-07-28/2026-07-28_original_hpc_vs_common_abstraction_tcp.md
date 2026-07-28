# Original HPC vs Common Abstraction Performance

## TCP Socket
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
Total test time: 5s 40ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.002s (= 2.002s total)
## Simulation execution time: 0h 0m 0.032s (= 0.032s total)
## Simulation stop time: 0h 0m 2.001s (= 2.001s total)
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
Total test time: 6s 38ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.005s (= 2.005s total)
## Simulation execution time: 0h 0m 0.029s (= 0.029s total)
## Simulation stop time: 0h 0m 2.001s (= 2.001s total)
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
Total test time: 5s 34ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.003s (= 2.003s total)
## Simulation execution time: 0h 0m 0.027s (= 0.027s total)
## Simulation stop time: 0h 0m 2.001s (= 2.001s total)
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
Total test time: 5s 46ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.002s (= 2.002s total)
## Simulation execution time: 0h 0m 0.037s (= 0.037s total)
## Simulation stop time: 0h 0m 2.001s (= 2.001s total)
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
Total test time: 6s 350ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.002s (= 2.002s total)
## Simulation execution time: 0h 0m 0.337s (= 0.337s total)
## Simulation stop time: 0h 0m 2.002s (= 2.002s total)
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
Total test time: 6s 299ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.002s (= 2.002s total)
## Simulation execution time: 0h 0m 0.289s (= 0.289s total)
## Simulation stop time: 0h 0m 2.001s (= 2.001s total)
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
Total test time: 5s 115ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.002s (= 2.002s total)
## Simulation execution time: 0h 0m 0.109s (= 0.109s total)
## Simulation stop time: 0h 0m 2.001s (= 2.001s total)
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
Total test time: 6s 40ms

####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 2.004s (= 2.004s total)
## Simulation execution time: 0h 0m 0.030s (= 0.030s total)
## Simulation stop time: 0h 0m 2.001s (= 2.001s total)
## Server uptime: None
####################################
</td>
</tr>
</table>
