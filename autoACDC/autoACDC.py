#!/usr/bin/env python

# Script: autoACDC.py
# Author: Luca Lavezzo
# Date: July 2022

import sys
import logging
from random import choice

sys.path.append('..')

from dbs.apis.dbsClient import DbsApi
import reqMgrClient as reqMgr
from utils import workflowInfo, siteInfo
from Unified.actor import singleRecovery

logging.basicConfig(level=logging.WARNING)


class autoACDC():
    """
    This class is meant to automatically submit ACDCs and assign them
    for a single task/workflow, and is based on makeACDC.py and assign.py.
    The main functions are
        makeACDC()
        assign()
    which are called by go(). Each of these two functions depends on some set
    of parameters, which are specified by the respective
        getACDCParameters()
        getAssignParameters()

    e.g.
    auto = autoACDC('<taskName>', xrootd=True, memory=4000)
    auto.go()
    """

    def __init__(self, taskName, **args):

        # class options, passed as args, used to set makeACDC and assign parameters
        self.options = {
            "testbed": args.get('testbed', False),
            "testbed_assign": args.get('testbed_assign', False),
            "include_sites": args.get('include_sites', None),
            "exclude_sites": args.get('exclude_sites', None),
            "xrootd": args.get('xrootd', False),
            "secondary_xrootd": args.get('secondary_xrootd', False),
            "memory": args.get('memory', None),
            "multicore": args.get('multicore', None),
            "splitting": args.get('splitting', None), # Uses: '(number)x', 'Same', 'max'
            "team": args.get('team', None),
            "replica": args.get('replica', False), # Adds a _Disk Non-Custodial Replica parameter
            "activity": args.get('activity'), # Dashboard Activity (reprocessing, production or test), if empty will set reprocessing as default
            "lfn": args.get('lfn'), # Merged LFN base
            "lumisperjob": args.get('lumisperjob', None), # Set the number of lumis per job
            "maxmergeevents": args.get('maxmergeevents', None), # Set the number of event to merge at max        
            "exceptions": args.get("exceptions", None)
        }

        # set the correct url
        if self.options['testbed'] or self.options['testbed_assign']: self.url = 'cmsweb-testbed.cern.ch' 
        else: self.url = 'cmsweb.cern.ch'

        # original task information, used to create an ACDC
        self.taskName = taskName    
        self.wfName = taskName.split("/")[1]
        self.wfInfo = workflowInfo(self.url, self.wfName)

        # to be created ACDC workflow info, used to assign
        self.acdcName = None
        self.acdcInfo = None
        self.schema = None

    def getRandomDiskSite(self, site=None):
        """
        Gets a random disk site and append _Disk
        """
        SI = siteInfo()
        if site is None:
            site = SI.sites_T1s
        s = choice(site)
        if s.startswith("T1"):
            s += "_Disk"
        return s

    def getRandomT1Site(self):
        """
        Gets a random T1 site.
        Makes sure it's available, and not excluded.
        Throws error if none match these criteria.
        Returns: site name.
        """

        # get all sites
        SI = siteInfo()
        sites = set(SI.all_sites)
        sites = [s for s in sites if 'T1' in s]

        # get only available ones
        sites = self.checkSites(sites)

        # make to exclude the desired sites
        if self.options['exclude_sites'] is not None:  sites = self.excludeSites(sites)
        
        # if no available, non-excluded T1 sites
        if len(sites) == 0:
            raise Exception("You have excluded all avilable T1 sites.")

        # get a random T1 site
        site = choice(sites)

        return site

    def checkSites(self, sites):
        """
        Checks whether all 'sites' are available.
        Turns on xrootd if some are down, raises exception if all are down.
        Returns: list of available sites, or exception.
        """

        SI = siteInfo()

        not_ready = sorted(set(sites) & set(SI.sites_not_ready))
        not_existing = sorted(set(sites) - set(SI.all_sites))
        not_matching = sorted((set(sites) - set(not_ready) - set(not_existing)))

        sites = sorted(set(sites) - set(not_ready) - set(not_existing))

        # if any (but not all) of the sites are down
        # enable xrootd and run anyways
        if len(sites) == 0:
            logging.info("None of the necessary sites are ready")
        elif len(not_ready) > 0: 
            logging.info("Some of the necessary sites are not ready:" + str(list(set(not_ready))))
            self.options['xrootd'] = True
            logging.warning("Set xrootd option to " + str(self.options['xrootd']))
        else:
            logging.info("All necessary sites are available")

        return sites

    def getACDCsites(self):
        """
        Gets the sites of the original workflow.
        Returns: list of sites.
        """

        SI = siteInfo()
        original_wf = workflowInfo(self.url, self.schema['OriginalRequestName']) 
            
        where_to_run, missing_to_run, missing_to_run_at =  original_wf.getRecoveryInfo()
        task = self.schema['InitialTaskPath']
        sites = list(set([SI.SE_to_CE(site) for site in where_to_run[task]]) & set(SI.all_sites))

        return sites

    def excludeT3Sites(self, sites):
        """
        Excludes T3 sites from the input sites. Should always be
        called for an ACDC.
        Returns: list of sites.
        """
        return [s for s in sites if 'T3' not in s]

    def includeSites(self, sites):
        """
        Include sites using the option of the class include_sites.
        Returns: list of sites.
        """

        if type(self.options['include_sites']) is not list: 
            raise Exception("Option 'include_sites' must be a list of strings.")

        sites = sorted(set(sites) | set(self.options['include_sites']))

        return sites

    def excludeSites(self, sites):
        """
        Excludes sites using the option of the class exclude_sites.
        Returns: list of sites.
        """

        if type(self.options['exclude_sites']) is not list: 
            raise Exception("Option 'exclude_sites' must be a list of strings.")

        sites = sorted(set(sites) - set(self.options['exclude_sites']))

        if len(sites) == 0:
            logging.info("No sites left after sites were excluded.")

        return sites

    def getSites(self):
        """
        Gets the sites to run on based on the original workflow,
        which are currently available, and which are excluded.
        Returns: list of sites.
        """

        sites = self.getACDCsites()

        # exclude T3 sites
        sites = self.excludeT3Sites(sites)

        # include sites
        if self.options['include_sites'] is not None: sites = self.includeSites(sites)

        # check if all desired sites are up and running
        sites = self.checkSites(sites)

        # provide a list of site names to exclude
        if self.options['exclude_sites'] is not None: sites = self.excludeSites(sites)

        # if no sites are left, sets to a random T1 site
        # it makes sure to check that it's available and not excluded
        if len(sites) == 0:
            logging.info("No sites available, setting to a random T1 site.")
            sites = [self.getRandomT1Site()]
            self.options['xrootd'] = True
            logging.warning("Set random site to " + str(sites))
            logging.warning("Set xrootd option to " + str(self.options['xrootd']))

        return sites

    def getTaskchainMemoryDict(self):
        """
        Returns: a dictionary of memory settings for taskchain.
        """

        memory = self.options['memory']
        increase = set_to = None
        tasks,set_to = memory.split(':') if ':' in memory else ("",memory)
        tasks = tasks.split(',') if tasks else []
        if set_to.startswith('+') and set_to.endswith("%"):
            percent_incrase = int(set_to[1:-1])
        elif set_to.startswith('+') and not set_to.endswith("%"):
            increase = int(set_to[1:])
        else:
            set_to = int(set_to)
        it = 1
        memory_dict = {}
        while True:
            t = 'Task%d'%it
            it += 1
            if t in  self.schema:
                tname = self.schema[t]['TaskName']
                if tasks and not tname in tasks:
                    memory_dict[tname] =  self.schema[t]['Memory']
                    continue
                if set_to:
                    memory_dict[tname] = set_to
                elif increase:
                    memory_dict[tname] = int(self.schema[t]['Memory'] + increase)
                elif percent_incrase:
                    memory_dict[tname] = int(self.schema[t]['Memory']*(1+(percent_incrase/100)))
            else:
                break

        return memory_dict

    def getTaskchainMulticoreDict(self):
        """
        Returns: a dictionary of multicore settings for taskchain.
        """

        multicore = self.options['multicore']
        tasks,set_to = multicore.split(':') if ':' in multicore else ("",multicore)
        tasks = tasks.split(',') if tasks else []
        set_to = int(set_to)
        multicore_dict = {}
        timeperevent_dict = {}
        it=1
        while True:
            t = 'Task%d'%it
            it += 1
            if t in self.schema:
                tname = self.schema[t]['TaskName']
                mcore = self.schema[t]['Multicore']
                if tasks and not tname in tasks:
                    multicore_dict[tname] = self.schema[t]['Multicore']
                    timeperevent_dict[tname] = self.schema[t]['TimePerEvent']
                    continue
                if self.options['memory']:
                    memory_dict = self.getTaskchainMemoryDict()
                    mem = memory_dict[tname]
                    factor = (set_to / float(mcore))
                    fraction_constant = 0.4
                    mem_per_core_c = int((1-fraction_constant) * mem / float(mcore))                    
                    memory_dict[tname] = mem + (set_to-mcore)*mem_per_core_c
                    timeperevent_dict[tname] = self.schema[t]['TimePerEvent']/factor
                multicore_dict[tname] = set_to
            else:
                break

        return multicore_dict, memory_dict


    def getMemory(self):
        """
        Sets memory to either:
            1. A numerical increase (e.g. +100 sets to original+100)
            2. A percentage increasse (e.g. +10% sets to original*(1.1))
            3. The memory passed in options (e.g. 1000 sets to 1000)
            4. If no options['memory'] is passed, returns False, memory is not changed from default.

        Returns: memory, either a value or boolean
        """
        memory_option = self.options['memory']
        original_memory = self.wfInfo.request.get('Memory')

        if memory_option:
            if memory_option.startswith("+") and not memory_option.endswith("%") and original_memory:
                increase = int(memory_option[1:])
                memory = int(original_memory + increase)
            elif memory_option.startswith("+") and memory_option.endswith("%") and original_memory:
                percent_incrase = int(memory_option[1:-1])
                memory = int(original_memory*(1 + (percent_incrase/100.0)))
            else:
                memory = memory_option
        else:
            memory = False

        return memory

    def getACDCParameters(self):
        """
        Returns: a list of actions based on the desired ACDC parameters.
        """

        memory = self.getMemory()

        actions = {}
        if memory:
            actions['memory'] =  memory
        if self.options['multicore']:
            actions['multicore'] = self.options['multicore']
        if self.options['xrootd']:
            actions['xrootd'] = bool(self.options['xrootd'])
        if self.options['splitting']:
            actions['split'] = self.options['splitting']

        return actions

    def setACDCWfInfo(self):
        """
        Sets the acdcInfo and schema of the submitted ACDC wf.
        """

        # grab the ACDC workflow information and schema
        self.acdcInfo = workflowInfo(self.url, self.acdcName)
        self.schema = self.acdcInfo.request

        # WF must be in Resubmission in order to be assigned
        if not (self.schema['RequestType'] == 'Resubmission') and not self.options['testbed_assign']: 
            raise Exception("RequestType is not 'Resubmission'")

        # WF must be in assignment-approved in order to be assigned
        if (self.schema["RequestStatus"] != "assignment-approved") and not self.options['testbed_assign']:
            raise Exception("RequestType is not 'assignment-approved'")

    def getPreviousWfs(self):
        """
        Returns: the first (ancestor) and last (original) workflow infos.
        """

        if 'OriginalRequestName' in self.schema.keys():
            original_wf = workflowInfo(self.url, self.schema['OriginalRequestName'])            
            ancestor_wf = workflowInfo(self.url, self.schema['OriginalRequestName'])
            ## go back as up as possible
            while ancestor_wf.request['RequestType'] == 'Resubmission':
                if 'OriginalRequestName' not in ancestor_wf.request:
                    ancestor_wf = None
                    break
                ancestor_wf = workflowInfo(self.url, ancestor_wf.request['OriginalRequestName'])
        else:
            raise Exception("'OriginalRequestName' not in schema.")

        return original_wf, ancestor_wf

    def getAssignParameters(self):
        """
        Defines a dictionary of paremeters for assign based on the
        original workflow, the ACDC created, and the options that
        are passed to the class.
        Returns: a dictionary of parameters for assign.
        """

        self.setACDCWfInfo()

        original_wf, ancestor_wf = self.getPreviousWfs()

        # check to see if the workflow is a task chain or an ACDC of a taskchain
        taskchain = (self.schema["RequestType"] == "TaskChain") or (ancestor_wf and ancestor_wf.request["RequestType"] == "TaskChain")

        # these are automatically determined from ancestor workflow
        era = ancestor_wf.acquisitionEra()
        procstring = ancestor_wf.processingString()
        if (not era or not procstring) or (taskchain and (type(era)!=dict or type(procstring)!=dict)):
            raise Exception("We do not have a valid AcquisitionEra and ProcessingString")
        procversion = ancestor_wf.request['ProcessingVersion']
        
        # some default options in case the arguments aren't passed

        # Must use --lfn option, otherwise workflow won't be assigned
        if self.options['lfn']:
            lfn = self.options['lfn']
        elif "MergedLFNBase" in self.schema.keys():
            lfn = self.schema['MergedLFNBase']
        elif ancestor_wf and "MergedLFNBase" in ancestor_wf.request:
            lfn = ancestor_wf.request['MergedLFNBase']
        else:
            raise Exception("Can't assign the workflow! Please include workflow lfn using --lfn option.")
        
        # activity production by default for taskchains, reprocessing for default by workflows
        if self.options['activity']:
            activity = self.options['activity']
        elif taskchain:
            activity = 'production'
        else:
            activity = 'reprocessing'   

        # inherit or overwrite
        if self.options['secondary_xrootd']:
            secondary_xrootd =  self.options['secondary_xrootd']
        elif ancestor_wf and "TrustPUSitelists" in ancestor_wf.request:
            secondary_xrootd = ancestor_wf.request['TrustPUSitelists']
        else:
            secondary_xrootd = False

        # get sites, and turn on xrootd in case we use a random site
        sites = self.getSites()

        # WARNING: this should be called after getSites(),
        # since the function can modify the xrootd settings.
        xrootd = bool(self.options['xrootd'])

        params = {
            "SiteWhitelist": sites,
            "MergedLFNBase": lfn,
            "Dashboard": activity,
            "ProcessingVersion": procversion,
            "execute": True,
            "AcquisitionEra": era,
            "ProcessingString": procstring,
            "TrustSitelists": xrootd,
            "TrustPUSitelists": secondary_xrootd
        }

        if self.options['replica']:
            params["NonCustodialSites"] = self.getRandomDiskSite(),

        if self.options['testbed_assign']:
            params['execute'] = False    

        if self.options['maxmergeevents'] is not None:
            params['MaxMergeEvents'] = self.options['maxmergeevents']

        if self.options['lumisperjob'] is not None:
            params['LumisPerJob'] = self.options['lumisperjob']

        if self.options['memory']: 
            if taskchain: params["Memory"] = self.getTaskchainMemoryDict()
            else: params["Memory"] = self.getMemory()
        if self.options['multicore']:
            if taskchain: 
                multicore_dict, memory_dict = self.getTaskchainMulticoreDict()
                params["Multicore"] = multicore_dict
                params["Memory"] = memory_dict
            else: params["Multicore"] = int(self.options['multicore'])

        if self.options['team'] is not None: params['Team'] = self.options['team']
        else: params['Team'] = self.schema['Team']

        return params

    def makeACDC(self):
        """
        Gets the ACDC parameters and submits the ACDC.
        """
        
        actions = self.getACDCParameters()
        logging.info("ACDC will be submitted with the following parameters:")
        logging.info(actions)

        # testing
        if self.options['testbed']:
            logging.info(self.taskName)
            sys.exit("Running with testbed on, quitting.")
            
        acdc = singleRecovery(self.url, self.taskName, self.wfInfo.request, actions, do=True)
        if acdc:
            # save the name of the newly created ACDC workflow
            logging.info("Submitted " + acdc)
            self.acdcName = acdc
        else:
            raise Exception("Could not create ACDC.")

    def assign(self):
        """
        Gets the assign parameters and assigns the workflow.
        """

        params = self.getAssignParameters()

        # deal with exceptions
        params = self.exceptions(params)

        # testing
        if self.options['testbed_assign']:
            logging.info(self.acdcName)
            logging.info(params)
            sys.exit("Running with testbed_assign on, quitting.")

        res = reqMgr.assignWorkflow(self.url, self.acdcName, params['Team'], params)
        if res:
            logging.info("Assigned " + self.acdcName)
        else:
            raise Exception("Could not assign workflow.")

    def go(self):
        """
        Run everything!
        """
        self.makeACDC()
        self.assign()

    def setACDCName(self, acdcName):
        """
        Supposing you only want to assign an already created ACDC,
        you can just set the acdcName here using this funciton, 
        and then call assign()

        e.g.
        auto = autoACDC('<taskName>', ...)
        auto.setACDCName('<acdcName>')
        auto.assign()
        """
        self.acdcName = acdcName

    def exceptions(self, params):
        """
        Manage some exceptions here by re-adjusting the assign paremeters,
        based on some parameters in the schema.
        For now, exceptions means hardcore setting the site.
        """
        if self.options['exceptions'] is not None:
            is_exception = self.check_keys(self.schema)
            if is_exception:
                logging.info("Found exception.")
                sites = self.getACDCsites()
                sites = self.checkSites(sites)
                if len(sites) == 0:
                    raise Exception("No sites available, can't assign workflow")
                params['SiteWhitelist'] = sites

        return params


    def check_keys(self, dictionary):
        """
        Recursively checks every key of a dictionary containing nested dictionaries of variable depth,
        in this case the params dictionary, for a key existing in our exceptions,
        and if it finds it, checks if the pattern in the exceptions is present in the params.
        Credit: chatGPT
        """
        if isinstance(dictionary, dict):
            for key in dictionary.keys():
                if key in self.options['exceptions'].keys():
                    if self.options['exceptions'][key] in dictionary[key]:
                        return True
                if self.check_keys(dictionary[key]):
                    return True
        return False