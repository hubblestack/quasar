THIS REPO IS DEPRECATED. PLEASE USE https://github.com/hubblestack/hubble-salt

.. _quasar_introduction:

Introduction
============

Quasar is Hubble's reporting system; a key component in visualizing your data.
Quasar gathers the data captured by Nova, Nebula and Pulsar and delivers it
directly to your logging or SIM/SEM system. Create dashboards, alerts and
correlations all using the SIM/SEM system you already have!

Note: dashboards not included :)

.. _quasar_installation:

Installation
============

Each of the four HubbleStack components have been packaged for use with Salt's
Package Manager (SPM). Note that all SPM installation commands should be done
on the *Salt Master*.

.. _quasar_installation_required_configuration:

Required Configuration
----------------------

Salt's Package Manager (SPM) installs files into ``/srv/spm/{salt,pillar}``.
Ensure that this path is defined in your Salt Master's ``file_roots``:

.. code-block:: yaml

    file_roots:
      - /srv/salt
      - /srv/spm/salt

.. note:: This should be the default value. To verify run: ``salt-call config.get file_roots``

.. tip:: Remember to restart the Salt Master after making this change to the configuration.

.. _quasar_installation_packages:

Installation (Packages)
-----------------------

Installation is as easy as downloading and installing a package. (Note: in
future releases you'll be able to subscribe directly to our HubbleStack SPM
repo for updates and bugfixes!)

.. code-block:: shell

    wget https://spm.hubblestack.io/quasar/hubblestack_quasar-2016.10.4-1.spm
    spm local install hubblestack_quasar-2016.10.4-1.spm

You should now be able to sync the new modules to your minion(s) using the
``sync_returners`` Salt utility:

.. code-block:: shell

    salt \* saltutil.sync_returners

Copy the ``hubblestack_quasar.sls.orig`` into your Salt pillar, dropping the
``.orig`` extension and target it to selected minions.

.. code-block:: shell

    base:
      '*':
        - hubblestack_quasar

.. code-block:: shell

    salt \* saltutil.refresh_pillar

Once these modules are synced you'll be ready to begin reporting data and events.

Skip to :ref:`Usage <quasar_usage>`.

.. _quasar_installation_manual:

Installation (Manual)
---------------------

Copy everything from ``_returners/`` into your ``salt/_returners/`` directory,
and sync it to the minions.

.. code-block:: shell

    git clone https://github.com/hubblestack/quasar.git hubblestack-quasar.git
    cd hubblestack-quasar.git
    mkdir -p /srv/salt/_returners
    cp _returners/*.py /srv/salt/_returners/
    cp pillar.example /srv/pillar/hubblestack_quasar.sls
    salt \* saltutil.sync_returners

Target the ``hubblestack_quasar.sls`` extension and target it to selected minions.

.. code-block:: shell

    base:
      '*':
        - hubblestack_quasar

.. code-block:: shell

    salt \* saltutil.refresh_pillar

Once these modules are synced you'll be ready to begin reporting data and events.

Installation (GitFS)
--------------------

This installation method subscribes directly to our GitHub repository, pinning
to a tag or branch. This method requires no package installation or manual
checkouts.

Requirements: GitFS support on your Salt Master.

**/etc/salt/master.d/hubblestack-quasar.conf**

.. code-block:: diff

    gitfs_remotes:
      - https://github.com/hubblestack/quasar:
        - base: v2016.10.4

.. tip:: Remember to restart the Salt Master after applying this change.

.. _quasar_usage:

Usage
=====

Each Quasar module has different requirements and settings. Please see your preferred module's documentation.

.. _quasar_configuration:

Configuration
=============

.. _quasar_under_the_hood:

Under The Hood
==============

.. _quasar_development:

Development
===========

.. _quasar_contribute:

Contribute
==========

If you are interested in contributing or offering feedback to this project feel
free to submit an issue or a pull request. We're very open to community
contribution.
