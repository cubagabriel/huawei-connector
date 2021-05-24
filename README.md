A wrapper class for python telnetlib.Telnet class that can send configuration commands directly to many Huawei core
network products (PGW, NBI) that uses plain text MML over TCP (telnet-like).

How to use it:

- you can setup your parameters in a YAML file like the example
- parse the YAML file, create an object and login
- depending on Huawei product, some commands may be needed before applying actual read or write commands (ie. REG VNFC, REG NE)
- you may use some standalone functions provided to get the raw response or only the return code
- logout when you are done