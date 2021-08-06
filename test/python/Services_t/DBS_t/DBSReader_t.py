#!/usr/bin/env python
"""
_DBSReader_t_
Unit test for the DBS helper class.
"""

import unittest
from unittest.mock import patch
from Services.DBS.DBSReader import DBSReader


class DBSReaderTest(unittest.TestCase):
    # There are many more blocks and files under these datasets
    # For now, test just one of each one
    invalidDataset = {
        "dataset": "/ggXToJPsiJPsi_JPsiToMuMu_M6p2_JPCZeroMinusPlus_TuneCP5_13TeV-pythia8-JHUGen/RunIIFall17pLHE-93X_mc2017_realistic_v3-v2/LHE",
        "status": "INVALID",
        "logical_file_name": "/store/data/RunIIFall17pLHE/ggXToJPsiJPsi_JPsiToMuMu_M6p2_JPCZeroMinusPlus_TuneCP5_13TeV-pythia8-JHUGen/LHE/93X_mc2017_realistic_v3-v2/00000/F63EBE9E-297A-EB11-A3D1-FA163E30235E.root",
    }

    validDataset = {
        "dataset": "/TT_Mtt-1000toInf_TuneCP5_PSweights_13TeV-powheg-pythia8/RunIIFall17MiniAODv2-PU2017_12Apr2018_94X_mc2017_realistic_v14_ext1-v1/MINIAODSIM",
        "status": "VALID",
        "run": 1,
        "block_name": "/TT_Mtt-1000toInf_TuneCP5_PSweights_13TeV-powheg-pythia8/RunIIFall17MiniAODv2-PU2017_12Apr2018_94X_mc2017_realistic_v14_ext1-v1/MINIAODSIM#f3b36c1a-9618-4b58-b4ed-d2d4ff5a281a",
        "logical_file_name": "/store/mc/RunIIFall17MiniAODv2/TT_Mtt-1000toInf_TuneCP5_PSweights_13TeV-powheg-pythia8/MINIAODSIM/PU2017_12Apr2018_94X_mc2017_realistic_v14_ext1-v1/230000/F29916D2-2910-EB11-91DC-FEC1FD6C28DA.root",
        "logical_file_name_base": "/store/mc",
        "lumis": 4805,
        "some_random_lumis": [22772, 351, 23436, 22804, 12048],
    }

    # This dataset is a little bit bigger than the other ones
    # So use it only when the function has a fix for run=1
    validDatasetNotRun1 = {
        "dataset": "/MET/Run2018A-12Nov2019_UL2018-v3/MINIAOD",
        "status": "VALID",
        "run": 315258,
        "lumis_by_run": {315258: [1]},
        "block_name": "/MET/Run2018A-12Nov2019_UL2018-v3/MINIAOD#bf7e0e72-f9c5-443c-9ab9-a8e1bbc8c62d",
        "logical_file_name": "/store/data/Run2018A/MET/MINIAOD/12Nov2019_UL2018-v3/230000/720A0B05-C8B4-0448-AF29-7F18F2440B5F.root",
        "parent": "/MET/Run2018A-v1/RAW",
    }

    def setUp(self) -> None:
        """
        _setUp_
        Initialize the API to point at the test server.
        """

        self.url = "https://cmsweb-prod.cern.ch/dbs/prod/global/DBSReader"
        super(DBSReaderTest, self).setUp()
        return

    def tearDown(self) -> None:
        """
        _tearDown_
        """
        super(DBSReaderTest, self).tearDown()
        return

    def testGetDBSStatus(self) -> None:
        """getDBSStatus gets DBS Status of a dataset"""
        dbsReader = DBSReader(self.url)
        status = dbsReader.getDBSStatus(self.invalidDataset.get("dataset"))
        isStr = isinstance(status, str)
        self.assertTrue(isStr)

        isFound = status == self.invalidDataset.get("status")
        self.assertTrue(isFound)

    def testGetFilesWithLumiInRun(self) -> None:
        """getFilesWithLumiInRun gets DBS files with lumi of a dataset and run"""
        # Test when run is 1
        dbsReader = DBSReader(self.url)
        files = dbsReader.getFilesWithLumiInRun(self.validDataset.get("dataset"), self.validDataset.get("run"))
        isList = isinstance(files, list)
        self.assertTrue(isList)

        isListOfDicts = isinstance(files[0], dict)
        self.assertTrue(isListOfDicts)

        isFound = False
        for file in files:
            if self.validDataset.get("logical_file_name") == file["logical_file_name"]:
                isFound = True
                break
        self.assertTrue(isFound)

        # Test when run is not 1
        files = dbsReader.getFilesWithLumiInRun(
            self.validDatasetNotRun1.get("dataset"), self.validDatasetNotRun1.get("run")
        )
        isList = isinstance(files, list)
        self.assertTrue(isList)

        isListOfDicts = isinstance(files[0], dict)
        self.assertTrue(isListOfDicts)

        isFound = False
        for file in files:
            if self.validDatasetNotRun1.get("logical_file_name") == file["logical_file_name"]:
                isFound = True
                break
        self.assertTrue(isFound)

    def testgetBlockName(self) -> None:
        """getBlockName gets the block name of a file"""
        dbsReader = DBSReader(self.url)
        block = dbsReader.getBlockName(self.validDataset.get("logical_file_name"))
        isStr = isinstance(block, str)
        self.assertTrue(isStr)

        isFound = block == self.validDataset.get("block_name")
        self.assertTrue(isFound)

    @patch("Cache.CacheManager.CacheManager.get")
    @patch("Cache.CacheManager.CacheManager.set")
    def testGetDatasetFiles(self, mock_set, mock_get) -> None:
        """getDatasetFiles gets files of a dataset"""
        # Test when details is False and validFileOnly is False
        mock_set.return_value = True
        mock_get.return_value = None
        dbsReader = DBSReader(self.url)
        files = dbsReader.getDatasetFiles(self.invalidDataset.get("dataset"))
        isList = isinstance(files, list)
        self.assertTrue(isList)

        isListOfDicts = isinstance(files[0], dict)
        self.assertTrue(isListOfDicts)

        noDetails = False
        for file in files:
            if any(k not in ["logical_file_name", "is_file_valid"] for k in file):
                break
        else:
            noDetails = True
        self.assertTrue(noDetails)

        isFound = False
        for file in files:
            if self.invalidDataset.get("logical_file_name") == file["logical_file_name"]:
                isFound = True
                break
        self.assertTrue(isFound)

        # Test when details is False and validFileOnly is True
        mock_set.return_value = True
        mock_get.return_value = None
        files = dbsReader.getDatasetFiles(self.invalidDataset.get("dataset"), validFileOnly=True)
        isList = isinstance(files, list)
        self.assertTrue(isList)

        isEmpty = len(files) == 0
        self.assertTrue(isEmpty)

    def testGetDatasetBlockNamesByRuns(self) -> None:
        """getDatasetBlockNamesByRuns gets the blocks names for a dataset filtered by runs"""
        # Test when run is 1
        dbsReader = DBSReader(self.url)
        blocks = dbsReader.getDatasetBlockNamesByRuns(self.validDataset.get("dataset"), [self.validDataset.get("run")])
        isList = isinstance(blocks, list)
        self.assertTrue(isList)

        isListOfStr = isinstance(blocks[0], str)
        self.assertTrue(isListOfStr)

        isFound = False
        for block in blocks:
            if block == self.validDataset.get("block_name"):
                isFound = True
                break
        self.assertTrue(isFound)

        # Test when run is not 1
        blocks = dbsReader.getDatasetBlockNamesByRuns(
            self.validDatasetNotRun1.get("dataset"),
            [self.validDatasetNotRun1.get("run")],
        )
        isList = isinstance(blocks, list)
        self.assertTrue(isList)

        isListOfStr = isinstance(blocks[0], str)
        self.assertTrue(isListOfStr)

        isFound = False
        for block in blocks:
            if block == self.validDatasetNotRun1.get("block_name"):
                isFound = True
                break
        self.assertTrue(isFound)

    def testGetDatasetBlockNamesByLumis(self) -> None:
        """getDatasetBlockNamesByLumis gets the blocks names for a dataset filtered by lumi sections"""
        dbsReader = DBSReader(self.url)
        blocks = dbsReader.getDatasetBlockNamesByLumis(
            self.validDatasetNotRun1.get("dataset"),
            self.validDatasetNotRun1.get("lumis_by_run"),
        )
        isList = isinstance(blocks, list)
        self.assertTrue(isList)

        isListOfStr = isinstance(blocks[0], str)
        self.assertTrue(isListOfStr)

        isFound = False
        for block in blocks:
            if block == self.validDatasetNotRun1.get("block_name"):
                isFound = True
                break
        self.assertTrue(isFound)

    def testGetDatasetBlockNames(self) -> None:
        """getDatasetBlockNames gets the blocks names for a dataset"""
        dbsReader = DBSReader(self.url)
        blocks = dbsReader.getDatasetBlockNames(self.validDataset.get("dataset"))
        isList = isinstance(blocks, list)
        self.assertTrue(isList)

        isListOfStr = isinstance(blocks[0], str)
        self.assertTrue(isListOfStr)

        isFound = False
        for block in blocks:
            if block == self.validDataset.get("block_name"):
                isFound = True
                break
        self.assertTrue(isFound)

    def testGetDatasetSize(self) -> None:
        """getDatasetSize gets the size of a dataset"""
        dbsReader = DBSReader(self.url)
        size = dbsReader.getDatasetSize(self.validDataset.get("dataset"))
        isFloat = isinstance(size, float)
        self.assertTrue(isFloat)

    def testGetDatasetEventsPerLumi(self) -> None:
        """getDatasetEventsPerLumi gets the number of events per lumis of a dataset"""
        dbsReader = DBSReader(self.url)
        eventsPerLumis = dbsReader.getDatasetEventsPerLumi(self.validDataset.get("dataset"))
        isFloat = isinstance(eventsPerLumis, float)
        self.assertTrue(isFloat)

    def testGetDatasetEventsAndLumis(self) -> None:
        """getDatasetEventsAndLumis gets number of events and lumis of a dataset"""
        dbsReader = DBSReader(self.url)
        events, lumis = dbsReader.getDatasetEventsAndLumis(self.validDataset.get("dataset"))
        for i in [events, lumis]:
            isInt = isinstance(i, int)
            self.assertTrue(isInt)

    def testGetBlocksEventsAndLumis(self) -> None
        """getBlocksEventsAndLumis gets number of events and lumis of blocks"""
        dbsReader = DBSReader(self.url)
        events, lumis = dbsReader.getBlocksEventsAndLumis([self.validDataset.get("block_name")])
        for i in [events, lumis]:
            isInt = isinstance(i, int)
            self.assertTrue(isInt)

    def testGetDatasetRuns(self) -> None:
        """getDatasetRuns gets the runs of a dataset"""
        dbsReader = DBSReader(self.url)
        runs = dbsReader.getDatasetRuns(self.validDataset.get("dataset"))
        isList = isinstance(runs, list)
        self.assertTrue(isList)

        isListOfInts = isinstance(runs[0], int)
        self.assertTrue(isListOfInts)

        isFound = runs[0] == self.validDataset.get("run")
        self.assertTrue(isFound)

    def testGetDatasetParent(self) -> None:
        """getDatasetParent gets the parents of a dataset"""
        dbsReader = DBSReader(self.url)
        parents = dbsReader.getDatasetParent(self.validDatasetNotRun1.get("dataset"))
        isList = isinstance(parents, list)
        self.assertTrue(isList)

        isListOfStr = isinstance(parents[0], str)
        self.assertTrue(isListOfStr)

        isFound = parents[0] == self.validDatasetNotRun1.get("parent")
        self.assertTrue(isFound)

    def testGetDatasetNames(self) -> None:
        """getDatasetNames gets the name of a dataset"""
        # Test when details is True
        dbsReader = DBSReader(self.url)
        names = dbsReader.getDatasetNames(self.validDataset.get("dataset"))
        isList = isinstance(names, list)
        self.assertTrue(isList)

        isListOfDicts = isinstance(names[0], dict)
        self.assertTrue(isListOfDicts)

        isFound = False
        for name in names:
            if name["dataset"] == self.validDataset.get("dataset"):
                isFound = True
                break
        self.assertTrue(isFound)

        # Test when details is False
        dbsReader = DBSReader(self.url)
        names = dbsReader.getDatasetNames(self.validDataset.get("dataset"), details=False)
        isList = isinstance(names, list)
        self.assertTrue(isList)

        isListOfStr = isinstance(names[0], str)
        self.assertTrue(isListOfStr)

        isFound = self.validDataset.get("dataset") in names
        self.assertTrue(isFound)

    def testGetLFNBase(self) -> None:
        """getLFNBase gets the base of the filenames of a dataset"""
        dbsReader = DBSReader(self.url)
        name = dbsReader.getLFNBase(self.validDataset.get("dataset"))
        isStr = isinstance(name, str)
        self.assertTrue(isStr)

        isFound = name == self.validDataset.get("logical_file_name_base")
        self.assertTrue(isFound)

    @patch("Cache.CacheManager.CacheManager.get")
    @patch("Cache.CacheManager.CacheManager.set")
    def testGetDatasetLumisAndFiles(self, mock_set, mock_get) -> None:
        """getDatasetLumisAndFiles gets lumi sections and files of a dataset"""
        mock_set.return_value = True
        mock_get.return_value = None
        dbsReader = DBSReader(self.url)
        results = dbsReader.getDatasetLumisAndFiles(self.validDataset.get("dataset"), withCache=False)
        isDict = all(isinstance(result, dict) for result in results)
        self.assertTrue(isDict)

        # Test first output value
        isKeyInt = all(isinstance(k, int) for k in list(results[0].keys())[:5])
        self.assertTrue(isKeyInt)

        isValueList = all(isinstance(v, list) for v in list(results[0].values())[:5])
        self.assertTrue(isValueList)

        isFound = False
        for k, v in results[0].items():
            if k == self.validDataset.get("run"):
                isFound = all(lumis in v for lumis in self.validDataset.get("some_random_lumis"))
                break
        self.assertTrue(isFound)

        # Test second output value
        isKeyTuple = all(isinstance(k, tuple) for k in list(results[1].keys())[:5])
        self.assertTrue(isKeyTuple)

        isValueList = all(isinstance(v, list) for v in list(results[1].values())[:5])
        self.assertTrue(isValueList)

        isFound = False
        for k, v in results[1].items():
            if k[0] == self.validDataset.get("run") and k[1] == self.validDataset.get("lumis"):
                isFound = self.validDataset.get("logical_file_name") in v
                break
        self.assertTrue(isFound)

    def testGetBlocksLumisAndFilesForCaching(self) -> None:
        """getBlocksLumisAndFilesForCaching gets lumi sections and files of blocks for caching"""
        dbsReader = DBSReader(self.url)
        blocks = [{"block_name": self.validDataset.get("block_name")}]
        results = dbsReader.getBlocksLumisAndFilesForCaching(blocks)
        isDict = all(isinstance(result, dict) for result in results)
        self.assertTrue(isDict)

        # Test first output value
        isKeyStr = all(isinstance(k, str) for k in list(results[0].keys())[:5])
        self.assertTrue(isKeyStr)

        isValueList = all(isinstance(v, list) for v in list(results[0].values())[:5])
        self.assertTrue(isValueList)

        isFound = False
        for k, v in results[0].items():
            if int(k) == self.validDataset.get("run"):
                isFound = all(lumis in v for lumis in self.validDataset.get("some_random_lumis"))
                break
        self.assertTrue(isFound)

        # Test second output value
        isKeyStr = all(isinstance(k, str) for k in list(results[1].keys())[:5])
        self.assertTrue(isKeyStr)

        isValueList = all(isinstance(v, list) for v in list(results[1].values())[:5])
        self.assertTrue(isValueList)

        isFound = False
        for k, v in results[1].items():
            if k == str(self.validDataset.get("run")) + ":" + str(self.validDataset.get("lumis")):
                isFound = self.validDataset.get("logical_file_name") in v
                break
        self.assertTrue(isFound)


if __name__ == "__main__":
    unittest.main()
