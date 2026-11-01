# Running the Haq server

One small Ubuntu 24.04 machine: Caddy takes https and passes requests to the API, which keeps
cases as files on the machine's disk. It runs as a single process, because its daily limits and
its list of running agents are held in memory. Back up `/var/lib/haq`, or take machine snapshots:
it holds the only copy of every case.

## Set up

1. Create the machine with a fixed public IP, and open only ports 22, 80 and 443.
2. Copy the repository to it, then run this with the public hostname. A free `sslip.io` name works
   without buying a domain: for the IP `1.2.3.4`, use `1-2-3-4.sslip.io`.

   ```bash
   sudo bash deploy/setup.sh 1-2-3-4.sslip.io
   ```

3. Put the API key in `/etc/haq/haq.env`, then start it:

   ```bash
   sudo systemctl restart haq
   curl https://1-2-3-4.sslip.io/health
   ```

## Settings

They live in `/etc/haq/haq.env`, which only root can read. `HAQ_PUBLIC=1` makes the server refuse
to start with a Contributor model, so real people's data cannot reach one. To change the daily
limit on agent runs, set `HAQ_MAX_RUNS_PER_DAY`; the default is 60.

## Update

```bash
sudo bash deploy/setup.sh 1-2-3-4.sslip.io
sudo systemctl restart haq
```

Restarting stops any run in progress; the app then offers the customer a retry.

## Old cases

A daily timer runs `python -m haq purge`, which deletes cases with no activity for 180 days, as
the [privacy policy](../docs/PRIVACY.md) promises.
