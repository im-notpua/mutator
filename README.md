# General

python version 3.10 required!

Packages required for One-Login
sudo apt-get install pkg-config libxml2-dev libxmlsec1-dev libxmlsec1-openssl
sudo apt-get install python3.10-dev

required python packages:
PyYAML
python3-saml



# TODOs

## Evaluation
- [ ] automatic evaluation of logged data
  - [ ] graphs, tables
- [ ] automatic crash eval(?)
- [ ] more in-depth eval
  - [ ] first occurrence of crash
  - [ ] compare variations of mutators
  - [ ] new findings vs how much code was found
- [ ] more libraries with QEMU
  - [ ] write wrapper (framework?)
- [ ] generate seeds only from XSD
  - [ ] compare performance against espresso
  - [ ] would help to apply approach to other protocols
- [ ] comparison against other fuzzers (Nautilus?)
  - [ ] requires grammar for SAML
- [ ] test against real application


## Implementation
- [ ] clean up
- [ ] better data logging
  - [ ] directly to csv, remove redundant logging
- [ ] performance optimization
  - [ ] more dry
- [ ] better naming for files
  - [ ] include cfg file and cmd arguments in dir?
- [ ] prioritize well-formed inputs
  - [ ] use queue_get instead of fuzz_count(?)
- [ ] redo metric implementation
- [ ] add new metrics (e.g., valid signature) / combine metrics
- [ ] feedback-driven mutators


## Documentation
- [ ] document code
- [ ] general instructions for usage


## Misc
- [ ] revisit mutator selection
  - [ ] are we missing any?
  - [ ] can we implement them more general?
- [ ] better test automation
  - [ ] start multiple tests in a row
    - [ ] needs clean state in between
  - [ ] notify about problems
  - [ ] include automatic evaluation?
- [ ] tests and CI(?)
- [ ] clean up code, docker, eval scripts, ...


## Focus for now
- [ ] Clean up and documentation
- [ ] Test bugs against real app
- [ ] Test Java libraries
- [ ] Select and implement a few useful extensions
- [ ] Compare against Nautilus
  - [ ] with simple XML grammar