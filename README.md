Note: this is still WIP


# Release Lock

Relase Lock is a simple Slack bot for managing a lock for given tasks among multiple people. When one person obtain the lock, no one else can have it in the meantime, until the lock is released/expired.


## Usage

### Locking


`/rlock <duration: Optional[int] = 60> <message: Optional[str]>`


obtains the lock and announce it in a given channel


### Unlocking


`/runlock`

will release the lock for given channel


### Lock expiration

10 minutes before the lock expiration, the lock owner will receive a message to give the person chance to extend the lock or release it already (in case the person forgot).


## Installation


Server part can be installed easily via

`python setup.py install`

Python 3 is required (tested with Python 3.6 only)


## TODO

- add configs for Circus

- add list of required env variables list

- add instructions for Slack App configuration
