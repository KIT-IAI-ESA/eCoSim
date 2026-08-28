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
Total time: 651ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: None
## Simulation execution time: 0h 0m 0.344s (= 0.344s total)
## Simulation stop time: 0h 0m 0.024s (= 0.024s total)
## Server uptime: 0h 0m 0.267s (= 0.267s total)
####################################
```
</td>
<td>
Total test time: 925ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.021s (= 0.021s total)
## Simulation execution time: 0h 0m 0.567s (= 0.567s total)
## Simulation stop time: 0h 0m 0.026s (= 0.026s total)
## Server uptime: None
####################################
```
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
Total time: 955ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: None
## Simulation execution time: 0h 0m 0.692s (= 0.692s total)
## Simulation stop time: 0h 0m 0.023s (= 0.023s total)
## Server uptime: 0h 0m 0.224s (= 0.224s total)
####################################
```
</td>
<td>
Total test time: 867ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.023s (= 0.023s total)
## Simulation execution time: 0h 0m 0.578s (= 0.578s total)
## Simulation stop time: 0h 0m 0.024s (= 0.024s total)
## Server uptime: None
####################################
```
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
Total time: 730ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: None
## Simulation execution time: 0h 0m 0.419s (= 0.419s total)
## Simulation stop time: 0h 0m 0.022s (= 0.022s total)
## Server uptime: 0h 0m 0.274s (= 0.274s total)
####################################
```
</td>
<td>
Total test time: 897ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.022s (= 0.022s total)
## Simulation execution time: 0h 0m 0.567s (= 0.567s total)
## Simulation stop time: 0h 0m 0.022s (= 0.022s total)
## Server uptime: None
####################################
```
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
Total time: 967ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: None
## Simulation execution time: 0h 0m 0.672s (= 0.672s total)
## Simulation stop time: 0h 0m 0.025s (= 0.025s total)
## Server uptime: 0h 0m 0.255s (= 0.255s total)
####################################
```
</td>
<td>
Total test time: 903ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.020s (= 0.020s total)
## Simulation execution time: 0h 0m 0.576s (= 0.576s total)
## Simulation stop time: 0h 0m 0.023s (= 0.023s total)
## Server uptime: None
####################################
```
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
Total time: 9s 975ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.038s (= 0.038s total)
## Simulation execution time: 0h 0m 9.505s (= 9.505s total)
## Simulation stop time: 0h 0m 0.035s (= 0.035s total)
## Server uptime: None
####################################
```
</td>
<td>
Total test time: 9s 472ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.027s (= 0.027s total)
## Simulation execution time: 0h 0m 8.173s (= 8.173s total)
## Simulation stop time: 0h 0m 0.032s (= 0.032s total)
## Server uptime: None
####################################
```
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
Total time: 6s 873ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.023s (= 0.023s total)
## Simulation execution time: 0h 0m 6.484s (= 6.484s total)
## Simulation stop time: 0h 0m 0.026s (= 0.026s total)
## Server uptime: None
####################################
```
</td>
<td>
Total test time: 6s 785ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.022s (= 0.022s total)
## Simulation execution time: 0h 0m 5.509s (= 5.509s total)
## Simulation stop time: 0h 0m 0.029s (= 0.029s total)
## Server uptime: None
####################################
```
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
Total time: 3s 871ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.018s (= 0.018s total)
## Simulation execution time: 0h 0m 3.603s (= 3.603s total)
## Simulation stop time: 0h 0m 0.019s (= 0.019s total)
## Server uptime: None
####################################
```
</td>
<td>
Total test time: 4s 86ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.020s (= 0.020s total)
## Simulation execution time: 0h 0m 2.940s (= 2.940s total)
## Simulation stop time: 0h 0m 0.019s (= 0.019s total)
## Server uptime: None
####################################
```
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
Total time: 770ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.033s (= 0.033s total)
## Simulation execution time: 0h 0m 0.467s (= 0.467s total)
## Simulation stop time: 0h 0m 0.029s (= 0.029s total)
## Server uptime: None
####################################
```
</td>
<td>
Total test time: 1s 649ms

```
####################################
##       SERVER MEASUREMENT       ##
####################################
## Simulation start time: 0h 0m 0.032s (= 0.032s total)
## Simulation execution time: 0h 0m 0.444s (= 0.444s total)
## Simulation stop time: 0h 0m 0.033s (= 0.033s total)
## Server uptime: None
####################################
```
</td>
</tr>
</table>
