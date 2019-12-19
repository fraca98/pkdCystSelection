import os
import unittest
import vtk, qt, ctk, slicer, numpy
from slicer.ScriptedLoadableModule import *
import logging

#
# pkdCystSelection
#

class pkdCystSelection(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "pkdCystSelection" # TODO make this more human readable by adding spaces
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Luca Fracassetti (Mario Negri)"] # replace with "Firstname Lastname (Organization)"
        self.parent.helpText = """Cyst Selection Algorithm"""
        self.parent.acknowledgementText = """Mario Negri Institute""" # replace with organization, grant and thanks.

#
# pkdCystSelectionWidget
#

class pkdCystSelectionWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        # Instantiate and connect widgets ...

        #
        # Parameters Area
        #
        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Input/Output"
        self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the dummy collapsible button
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        #
        # labeled volume selector
        #
        self.LabeledVolumeSelector = slicer.qMRMLNodeComboBox()
        self.LabeledVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.LabeledVolumeSelector.selectNodeUponCreation = False
        self.LabeledVolumeSelector.addEnabled = False
        self.LabeledVolumeSelector.removeEnabled = False
        self.LabeledVolumeSelector.noneEnabled = False
        self.LabeledVolumeSelector.showHidden = False
        self.LabeledVolumeSelector.showChildNodeTypes = True
        self.LabeledVolumeSelector.setMRMLScene( slicer.mrmlScene )
        self.LabeledVolumeSelector.setToolTip( "Pick the input to the algorithm." )
        parametersFormLayout.addRow("Labeled Volume (T2_floodfilled): ", self.LabeledVolumeSelector)
        
        #
        # selected volume selector
        #
        self.SelectedVolumeSelector = slicer.qMRMLNodeComboBox()
        self.SelectedVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.SelectedVolumeSelector.selectNodeUponCreation = False
        self.SelectedVolumeSelector.addEnabled = False
        self.SelectedVolumeSelector.removeEnabled = False
        self.SelectedVolumeSelector.noneEnabled = False
        self.SelectedVolumeSelector.showHidden = False
        self.SelectedVolumeSelector.showChildNodeTypes = True
        self.SelectedVolumeSelector.setMRMLScene( slicer.mrmlScene )
        self.SelectedVolumeSelector.setToolTip( "Pick the input to the algorithm." )
        parametersFormLayout.addRow("Selected Volume(T2_labeled_ok): ", self.SelectedVolumeSelector)
        #
        #Cast button
        #
        self.CastButton = qt.QPushButton("Cast Int")
        self.CastButton.enabled = True
        parametersFormLayout.addRow(self.CastButton)
        
        #
        #Save Path Button
        #
        self.SavePath=qt.QPushButton("Set Save Path")
        self.SavePath.enabled=False
        parametersFormLayout.addRow(self.SavePath)
        
       
        #
        #Start Selection button
        #
        
        self.ActivateSelectionButton=qt.QPushButton("Start selecting")
        self.ActivateSelectionButton.enabled = False
        self.ActivateSelectionButton.setCheckable(True)
        parametersFormLayout.addRow(self.ActivateSelectionButton)
        
        #
        #Save Editor button
        #
        self.SaveEditor=qt.QPushButton("Save editor")
        self.SaveEditor.enabled = False
        parametersFormLayout.addRow(self.SaveEditor)
        
        
        
        self.Selecting = False
        
        
        #connections
        
        self.SavePath.connect('clicked(bool)',self.SavePathClicked)
        self.CastButton.connect('clicked(bool)', self.CastButtonClicked)
        self.ActivateSelectionButton.connect('clicked(bool)', self.ActivateSelectionButtonClicked)
        self.SaveEditor.connect('clicked(bool)',self.SaveEditorButtonClicked)
        
        # Add vertical spacer
        self.layout.addStretch(1)
        
        
        
    def cleanup(self):
        pass

    def SavePathClicked(self):
        self.SaveFile=qt.QFileDialog.getOpenFileName()
        print("Path selected:")
        print(self.SaveFile)
        self.SavePath.setStyleSheet("background-color: green")
        self.ActivateSelectionButton.enabled=True
        self.SaveEditor.enabled=True
        
    def CastButtonClicked(self):
        
        self.LabeledVolumeSelector.setEnabled(False) #disable qMRMLNodeComboBox
        self.SelectedVolumeSelector.setEnabled(False)

        self.CastButton.enabled=False
        self.SavePath.enabled=True

        
    def ActivateSelectionButtonClicked(self):
        if self.Selecting:
            self.ActivateSelectionButton.setText("Start selecting")
            self.ActivateSelectionButton.setCheckable(True)
            self.ActivateSelectionButton.setStyleSheet("background-color: white")
            self.Selecting = False

            self.interactor.RemoveObserver(self.TagRedInteractor)
            
            
            
        else:
            self.ActivateSelectionButton.setText("End selecting")
            self.ActivateSelectionButton.setCheckable(False)
            self.ActivateSelectionButton.setStyleSheet("background-color: red")
            self.Selecting = True

            def ConvertCoordinates2RAS(coordinates):
                inPoint = [coordinates[0], coordinates[1], 0, 1]
                matrixRAS = slicer.app.layoutManager().sliceWidget("Red").sliceLogic().GetSliceNode().GetXYToRAS()
                rasPoint = matrixRAS.MultiplyPoint(inPoint) #*inPoint
                return rasPoint
            
            def ConvertCoordinates2IJK(coordinates):
                rasPoint = ConvertCoordinates2RAS(coordinates)
                rasToIJKMatrix = vtk.vtkMatrix4x4()
                if not self.LabeledVolumeSelector.currentNode():
                    return None
                self.LabeledVolumeSelector.currentNode().GetRASToIJKMatrix(rasToIJKMatrix)
                ijkPoint = rasToIJKMatrix.MultiplyPoint(rasPoint) #*rasPoint
                return ijkPoint
            
            def onClick(caller,event):
                coordinates = self.interactor.GetLastEventPosition()
                ctrlKey = self.interactor.GetControlKey()
                rasPoint = ConvertCoordinates2RAS(coordinates)
                ijkPoint = ConvertCoordinates2IJK(coordinates)
                ijk = [int(round(i)) for i in ijkPoint[0:3]]
                labeledImage = self.LabeledVolumeSelector.currentNode().GetImageData() #GetImageData()
                selectedImage = self.SelectedVolumeSelector.currentNode().GetImageData()
                pointId = labeledImage.ComputePointId(ijk) #*
                targetLabel = int(round(labeledImage.GetScalarComponentAsFloat(ijk[0],ijk[1],ijk[2],0)))
                selectedLabel = int(round(selectedImage.GetScalarComponentAsFloat(ijk[0],ijk[1],ijk[2],0)))
                
                
                labeledArray=slicer.util.arrayFromVolume(self.LabeledVolumeSelector.currentNode())
                labeledSlice=labeledArray[ijk[2],...]
                
                
                selectedArray=slicer.util.arrayFromVolume(self.SelectedVolumeSelector.currentNode())
                selectedSlice=selectedArray[ijk[2],...]
                
                if not ctrlKey:
                    selectedSlice[labeledSlice == targetLabel] = targetLabel
                else:
                    selectedSlice[selectedSlice == selectedLabel] = 0


                self.SelectedVolumeSelector.currentNode().Modified()
                
                
                
                storageNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
                storageNode.SetFileName(self.SaveFile)  #SAVE
                storageNode.WriteData(self.SelectedVolumeSelector.currentNode())
                print("SAVED")
                
            
            #definire interactor
            self.interactor = slicer.app.layoutManager().sliceWidget("Red").interactorStyle().GetInteractor()
            self.TagRedInteractor=self.interactor.AddObserver("LeftButtonReleaseEvent", onClick)
    
    def SaveEditorButtonClicked(self):
        storageNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
        storageNode.SetFileName(self.SaveFile)
        storageNode.WriteData(self.SelectedVolumeSelector.currentNode())
        print("SAVED EDITOR")



class pkdCystSelectionTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)
    def runTest(self):
        self.setUp()
        self.test_pkdCystSelection1()
    def test_pkdCystSelection1(self):
        self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
        import SampleData
        SampleData.downloadFromURL(
        nodeNames='FA',
        fileNames='FA.nrrd',
        uris='http://slicer.kitware.com/midas3/download?items=5767')
        self.delayDisplay('Finished with download and loading')
        volumeNode = slicer.util.getNode(pattern="FA")
        logic = pkdCystSelectionLogic()
        self.assertIsNotNone( logic.hasImageData(volumeNode) )
        self.delayDisplay('Test passed!')
