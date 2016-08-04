Introduction
============

Quasar is Hubble's reporting system; a key component in visualizing your data.
Quasar gathers the data captured by Nova, Nebula and Pulsar and delivers it
directly to your logging or SIM/SEM system. Create dashboards, alerts and
correlations all using the SIM/SEM system you already have!

Note: dashboards not included :)

Installation
============

Each of the four HubbleStack components have been packaged for use with Salt's
Package Manager (SPM). Note that all SPM installation commands should be done
on the *Salt Master*.

**Required Configuration**

Salt's Package Manager (SPM) installs files into `/srv/spm/{salt,pillar}`.
Ensure that this path is defined in your Salt Master's `file_roots`:

.. code-block:: yaml

    file_roots:
      - /srv/salt
      - /srv/spm/salt

.. note:: This should be the default value. To verify run: `salt-call config.get file_roots`

.. tip:: Remember to restart the Salt Master after making this change to the configuration.

Installation (Packages)
-----------------------

Installation is as easy as downloading and installing a package. (Note: in
future releases you'll be able to subscribe directly to our HubbleStack SPM
repo for updates and bugfixes!)

.. code-block:: shell

    wget https://spm.hubblestack.io/2016.7.0_RC1/hubblestack_quasar-2016.7.0_RC1-1.spm
    spm local install hubblestack_quasar-2016.7.0_RC1-1.spm

You should now be able to sync the new modules to your minion(s) using the
`sync_returners` Salt utility:

.. code-block:: shell

    salt \* saltutil.sync_returners

Once these modules are synced you'll be ready to begin reporting data and events.

Skip to [Usage].

Installation (Manual)
---------------------

Copy everything from ``<hubblestack-quasar/_returners/>`` into your ``_returners/`` directory in your Salt
fileserver (whether roots or gitfs) and sync it to the minion(s).

.. code-block:: shell

    git clone https://github.com/hubblestack/quasar.git hubblestack-quasar.git
    cd hubblestack-quasar.git
    mkdir -p /srv/salt/_returners
    cp _returners/*.py /srv/salt/_returners/
    salt \* saltutil.sync_returners

Usage
=====

Each Quasar module has different requirements and settings. Please see your preferred module's documentation.

Configuration
=============

Under The Hood
==============

Development
===========

Contribute
==========

If you are interested in contributing or offering feedback to this project feel
free to submit an issue or a pull request. We're very open to community
contribution.
