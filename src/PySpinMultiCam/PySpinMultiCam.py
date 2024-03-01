import PySpin as pyspin
import pdb
import time;

def listCams():
 
    system = pyspin.System.GetInstance()
    AttachedCameras = system.GetCameras();
    CameraList=[];
    
    #Get Serial #'s for every Cam
    for i in range(AttachedCameras.GetSize()):
        cam=AttachedCameras.GetByIndex(i)       
        node_device_serial_number = pyspin.CStringPtr(cam.GetTLDeviceNodeMap().GetNode('DeviceSerialNumber'))        
        CameraList.append(node_device_serial_number.ToString())

    del AttachedCameras #Clean Up
    del cam;    
    system.ReleaseInstance();
    
    return CameraList
    

class MultiCamObj:

    camcount=0;
    cam=[]
    system=[];
    pixelformat=[];
    width=[];
    height=[];
    framerate=[];
    exposure=[];
    exposuretime=[];
    serials='';
    
    def __init__(self, *serials):
        
        try:
            self.serials=serials;        
            self.camcount=len(serials);
            
            for i in serials:
                print(i);

            self.system = pyspin.System.GetInstance()
            AttachedCameras = self.system.GetCameras()

            if (AttachedCameras.GetSize() < self.camcount):
                raise ValueError('Not enough devices for the requested # of Cameras');

            for i in range(self.camcount):
               self.cam.append(AttachedCameras.GetBySerial(serials[i])) #assign Cam to device                            
               self.cam[i].Init() # initialize
           
            # Set Cam #1 with driver setup on Hirose 
            self.cam[0].LineSelector.SetValue(pyspin.LineSelector_Line2)
            self.cam[0].V3_3Enable.SetValue(True)
            self.cam[0].AcquisitionFrameRateEnable.SetValue(True)
            self.cam[0].ExposureAuto.SetValue(True)            
            s_node_map = self.cam[0].GetTLStreamNodeMap()
            #Up buffers and set to OldestFirst (defaults to newest, fucking assholes)
            
            buffer_count = pyspin.CIntegerPtr(s_node_map.GetNode('StreamBufferCountManual'))
            #pdb.set_trace();
            buffer_count.SetValue(buffer_count.GetMax());
            print(buffer_count.GetMax());
            handling_mode = pyspin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
            handling_mode_entry = handling_mode.GetEntryByName('OldestFirst')
            handling_mode.SetIntValue(handling_mode_entry.GetValue())            
            self.pixelformat=self.cam[0].PixelFormat();
            self.height.append(self.cam[0].Height());
            self.width.append(self.cam[0].Width());        
            self.framerate=self.cam[0].AcquisitionFrameRate();           
            self.exposuretime=(self.cam[0].ExposureTime())/1000;
            
            if (self.camcount > 1):
                for i in range(1,self.camcount):   #Syncing setup for follower BlackFlys.                    
                    self.cam[i].TriggerMode.SetValue(pyspin.TriggerMode_Off)
                    self.cam[i].TriggerSource.SetValue(pyspin.TriggerSource_Line3)
                    self.cam[i].TriggerOverlap.SetValue(pyspin.TriggerOverlap_ReadOut)
                    self.cam[i].TriggerMode.SetValue(pyspin.TriggerMode_On)
                    self.height.append(self.cam[i].Height()); #SensorHeight for unbinned!
                    self.width.append(self.cam[i].Width());                    
                   # self.cam[i].AcquisitionFrameRateEnable.SetValue(False)
                  #  self.cam[i].ExposureAuto.SetValue(True)
                    s_node_map = self.cam[i].GetTLStreamNodeMap()
                    buffer_count = pyspin.CIntegerPtr(s_node_map.GetNode('StreamBufferCountManual'))
                    buffer_count.SetValue(buffer_count.GetMax());
                    handling_mode = pyspin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
                    handling_mode_entry = handling_mode.GetEntryByName('OldestFirst')
                    handling_mode.SetIntValue(handling_mode_entry.GetValue())
                    
           
        except ValueError as err:
            print(err.args)
         

    def __del__(self):
        self.system.ReleaseInstance();        
 
    def SetSingleFrame(self):
        try:
            for i in range(self.camcount):            
               self.cam[i].AcquisitionMode.SetValue(pyspin.AcquisitionMode_SingleFrame)
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False;

    def SetContinous(self):
        try:
            for i in range(self.camcount):            
               self.cam[i].AcquisitionMode.SetValue(pyspin.AcquisitionMode_Continuous)
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False;
        
    #def GetExposureMode(self,mode):

    def SetExposureMode(self,mode):
     """sets the exposure mode of the camera.  Mode should be once, continuous, or off."""
     if mode=='once':
      try:
       for i in range(self.camcount):            
               self.cam[i].AcquisitionMode.SetValue(pyspin.AcquisitionMode_SingleFrame)
       return True
      except pyspin.SpinnakerException as ex:
       print('Error: %s' % ex)
       return False
     elif mode=='continuous': 
      try:
       for i in range(self.camcount):            
               self.cam[i].AcquisitionMode.SetValue(pyspin.AcquisitionMode_Continuous)
       return True
      except pyspin.SpinnakerException as ex:
       print('Error: %s' % ex)
       return False
     elif mode =='off':
      try:
       for i in range(self.camcount):            
               self.cam[i].AcquisitionMode.SetValue(pyspin.ExposureAuto_Off)          
       return True
      except pyspin.SpinnakerException as ex:
       print('Error: %s' % ex)
       return False
     else: 
      print('Invalid exposure mode.  It should be once, continuous, or off.')
      return False
        
    def Start(self):
        try:            
            for i in range(1,self.camcount): #start secondary cameras;
              self.cam[i].BeginAcquisition();
            self.cam[0].BeginAcquisition();  # then start primary;
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False;

    def Stop(self):
        try:
            for i in range(self.camcount): #Stop beginning at the primary;
              self.cam[i].EndAcquisition();
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False;          

    def FramesInBuffer(self):
        # Only primary camera should matter- everything else should be synced. So only return its
        # buffer as representative of the entire MultiCam system. 
        FramesRemaining=self.cam[0].TransferQueueCurrentBlockCount()        
        return FramesRemaining;

    def GetNextImage(self):         
        Images=[];
        try:                     
                for i in range(self.camcount):                  
                   image=self.cam[i].GetNextImage(1000);
                   im = image.GetNDArray()
                   Images.append(im)
                   image.Release()
                   
        except pyspin.SpinnakerException as ex:
              print('Error: %s' % ex)
              return False;
        return Images;

    def SnapImage(self):         
        Images=[];
        self.SetExposureMode('once');
        t=self.cam[0].AcquisitionMode.GetCurrentEntry()
        OldValues=t.GetDisplayName()
        self.Start();       
        
        try:                     
                for i in range(self.camcount):                   
                   image=self.cam[i].GetNextImage(1000);
                   im = image.GetNDArray()
                   Images.append(im)
                   image.Release()
                   
        except pyspin.SpinnakerException as ex:
              print('Error: %s' % ex)
              return False;
        self.Stop();
 
        self.SetExposureMode('continuous');
   
        return Images;    

    def GetAllBufferedImages(self):
                
        images=[]
        try:
            for j in range(self.FramesInBuffer()):
                for i in range(self.camcount):

                   image=self.cam[i].GetNextImage(1000);
                   im = image.GetNDArray()
                   images.append(im)
                   image.Release()
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False;
        return images;      # Return all appended images;

    def SetExposureTime(self,exposure): # in uS
        try:            
            # Set 1st Cam, others follow.

            for j in range(self.camcount):
                self.cam[j].ExposureAuto.SetValue(pyspin.ExposureAuto_Off)
                #exposure = min(self.cam[0].ExposureTime.GetMax(), exposure*1000)
                self.cam[j].ExposureTime.SetValue(exposure*1000);
                self.exposuretime=self.cam[0].ExposureTime()/1000;
                self.cam[j].AcquisitionFrameRateEnable.SetValue(True)
                framerate=1/(self.exposuretime/1000)
                self.cam[j].AcquisitionFrameRate.SetValue(framerate);
                self.framerate=self.cam[0].AcquisitionFrameRate();
                       
            return self.exposuretime;
        
        except pyspin.SpinnakerException as ex:
           print('Error: %s' % ex)
           return False         
        
    def SetFrameRate(self,rate): #in Hz
        try:
            # Set 1st Cam, others follow.
            for j in range(self.camcount):
                self.cam[j].AcquisitionFrameRateEnable.SetValue(True)
                self.cam[j].AcquisitionFrameRate.SetValue(rate);
                self.cam[j].ExposureAuto.SetValue(pyspin.ExposureAuto_Off)
                self.framerate=self.cam[0].AcquisitionFrameRate();
                uSExposureTime= (1000/self.framerate)*1000
        #    print(uSExposureTime)
      #      pdb.set_trace()            
                self.cam[j].ExposureTime.SetValue(uSExposureTime)
                self.exposuretime=self.cam[j].ExposureTime()/1000;
            return self.framerate;
        
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False          

    def AcquireImageSequence(self, framecount):
        from PIL import Image
        
        try:            
            timeout=500; # Something has gone wrong at this point.
            
            for i in range(framecount):
                  for j in range(self.camcount):    
                      image=self.cam[j].GetNextImage(timeout)
                      im = (image.GetNDArray())
                      images.append(im)
                      image.Release()
            return images    
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False          

    def SetBinning(self, binningradius):
        try:                                  
           for j in range(self.camcount):    
                      self.cam[j].BinningVertical.SetValue(binningradius);
                      self.cam[j].BinningHorizontal.SetValue(binningradius);                      
                      self.height[j]=(self.cam[j].Height());
                      self.width[j]=(self.cam[j].Width());        
      
                        
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False           
        
    def SaveImageSequenceAVI(self, framecount, filename):
        import os

        try:            
            timeout=500; # Something has gone wrong at this point.
            avi_handler=[];
            avi_header_settings=[];
           # tme=int(time.time())
            for j in range(self.camcount):
                
                avi_handler.append(pyspin.SpinVideo());
                avi_header_settings.append(pyspin.AVIOption());
                avi_header_settings[j].frameRate=self.framerate;
                avi_header_settings[j].height=self.height[j];
                avi_header_settings[j].width=self.width[j];

                filename_camJ=f'{filename}_CAM{j}' # filename with camera info 
                avi_handler[j].Open(filename_camJ,avi_header_settings[j])

            i=0;    
            #while (0< framecount): #for i in range(framecount):
                           
               #if (self.FramesInBuffer()>1):                       
            for j in range(self.camcount):    
                      image=self.cam[j].GetNextImage()                      
                      avi_handler[j].Append(image)
                      image.Release()
                      i=i+1;
                        
            for j in range(self.camcount):                       
                avi_handler[j].Close()
                
            FailedCount=self.CheckLostFrames();
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return FailedCount
    
    def SaveImageTimeSeriesAVI(self, time, filename): #in S
        from math import ceil

        framecount=ceil(self.framerate*time);
        print(framecount)
        try:            
            timeout=500; # Something has gone wrong at this point.
            avi_handler=[];
            avi_header_settings=[];
          #  tme=int(time.time())
                                  
            for j in range(self.camcount): 
                avi_handler.append(pyspin.SpinVideo());
                avi_header_settings.append(pyspin.AVIOption());
                avi_header_settings[j].frameRate=self.framerate;
                avi_header_settings[j].height=self.height[j];
                avi_header_settings[j].width=self.width[j];    

                filename_camJ=f'{filename}_CAM{j}' # filename with camera info 
                avi_handler[j].Open(filename_camJ,avi_header_settings[j])

            for i in range(framecount):
                  for j in range(self.camcount):    
                      image=self.cam[j].GetNextImage()                      
                      avi_handler[j].Append(image)
                      image.Release()
                      
                      
            for j in range(self.camcount):                       
                avi_handler[j].Close()
        
            # FailedCount=self.CheckLostFrames();
            # print(FailedCount)                      
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
       # return FailedCount
    
    def SaveImageSequenceTIFF(self, framecount, filename): 
        from libtiff import TIFF
        from PIL import Image
        
        try:            
            timeout=500; # Something has gone wrong at this point.
            tif_handler=[];
            tif_header=[];
           # tme=int(time.time())
            for j in range(self.camcount):
                
                filename_camJ=f'{filename}_CAM{j}' # filename with camera info 
                tif_handler.append(TIFF.open(filename_camJ, mode = 'w'));                
                
            for i in range(framecount):
                  for j in range(self.camcount):
                      
                      image=self.cam[j].GetNextImage()
                      
                      im = Image.fromarray(image.GetNDArray())                      
                #      im = im.resize((int(self.cam[j].Width()),int(self.cam[j].Height())), Image.Resampling.LANCZOS)                        
                      tif_handler[j].write_image(im, compression = None)                      
                        
            for j in range(self.camcount):                       
                tif_handler[j].close()
            FailedCount=self.CheckLostFrames()
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return FailedCount

    def SaveImageTimeSeriesTIFF(self, framecount, filename): 
        from libtiff import TIFF
        from PIL import Image
        from math import ceil
        
        framecount=ceil(self.framerate*time);
        try:            
            timeout=500; # Something has gone wrong at this point.
            tif_handler=[];
            tif_header=[];
            
            for j in range(self.camcount):
                
                filename_camJ=f'{filename}_CAM{j}' # filename with camera info 
                tif_handler.append(TIFF.open(filename_camJ, mode = 'w'));                
                
            for i in range(framecount):
                  for j in range(self.camcount):
                      
                      image=self.cam[j].GetNextImage()                      
                      im = Image.fromarray(image.GetNDArray())                
                      tif_handler[j].write_image(im, compression = None)                      
                        
            for j in range(self.camcount):                       
                tif_handler[j].close()
        
            FailedCount=self.CheckLostFrames();
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return FailedCount 

    def CheckLostFrames(self): # X,Y Offsets, Width, Height
        
            MissingFramesCount=[0]*self.camcount;
            try:
                for j in range(self.camcount):
                    s_node_map = self.cam[j].GetTLStreamNodeMap()
                    LostFrames = pyspin.CIntegerPtr(s_node_map.GetNode('StreamLostFrameCount'))
                    MissingFramesCount[j]=LostFrames.GetValue();
            except pyspin.SpinnakerException as ex:
                print('Error: %s' % ex);
            return MissingFramesCount;   
    #### Testing stuff

    def SetBufferSize(self, bufsize): # X,Y Offsets, Width, Height
            

            try:
                for j in range(self.camcount):
                    s_node_map = self.cam[j].GetTLStreamNodeMap()
                    buffer_count = pyspin.CIntegerPtr(s_node_map.GetNode('StreamBufferCountManual'))
                    buffer_count.SetValue(bufsize);                
            except pyspin.SpinnakerException as ex:
                print('Error: %s' % ex);
            return False ;
        
    def ClearROI(self): # X,Y Offsets, Width, Height        
            
            try:
                for j in range(self.camcount):
                    
                    self.cam[j].OffsetY.SetValue(0)
                    self.cam[j].OffsetX.SetValue(0)
                    self.cam[j].Width.SetValue(self.cam[j].WidthMax())
                    self.cam[j].Height.SetValue(self.cam[j].HeightMax())
                    self.height[j]=self.cam[j].Height();
                    self.width[j]=self.cam[j].Width();                    
            except pyspin.SpinnakerException as ex:
                print('Error: %s' % ex);
            return False
        
    def SetROI(self, rois): # X,Y Offsets, Width, Height

            from math import ceil, floor                            
            try:
                
                for j in range(self.camcount):                    
                    #self.cam[j].AasRoiEnable.SetValue(True);
                    
                   # pdb.set_trace();
                    
                    #Round up widths, must be divisible by 4.
                    
                    ScaledbyFour=ceil(rois[j][2]/4)*4;
                    self.cam[j].Width.SetValue(ScaledbyFour)
                    ScaledbyFour=ceil(rois[j][3]/4)*4;
                    self.cam[j].Height.SetValue(ScaledbyFour)

                    #Round down Offsets
                    ScaledbyFour=floor(rois[j][0]/4)*4;
                    self.cam[j].OffsetX.SetValue(ScaledbyFour)
                    ScaledbyFour=floor(rois[j][1]/4)*4;
                    self.cam[j].OffsetY.SetValue(ScaledbyFour)
                    self.height[j]=self.cam[j].Height(); #self.cam[j].Height();
                    self.width[j]=self.cam[j].Width(); #self.cam[j].Width();
                    print('Camera ' + str(j) + ' -> ' +str(self.height[j]) + ' x ' + str(self.width[j]))
                          
                    
            except pyspin.SpinnakerException as ex:
                print('Error: %s' % ex);
            return False    
#### Testing stuff
##import cv2
#cams=listCams();
#amc=MultiCamObj(cams[0]); #The 2 color blackfly
##amc.ClearROI();
##rois=[]
##j=0
##Images=amc.SnapImage();
##roi=cv2.selectROI('Choose ROI - Enter to select, "c" to cancel',Images[0])
##rois.append(roi);
##cv2.destroyAllWindows()
##amc.SetROI(rois)
##amc.cam[j].AasRoiEnable.SetValue(True);                    
##amc.cam[j].AasRoiWidth.SetValue(rois[j][2])
##amc.cam[j].AasRoiHeight.SetValue(rois[j][3])                    
##amc.cam[j].AasRoiOffsetX.SetValue(rois[j][0])
##amc.cam[j].AasRoiOffsetY.SetValue(rois[j][1])
#amc.height[j]=amc.cam[j].Height();
#amc.width[j]=amc.cam[j].Width();
#Images=amc.SnapImage();

#amc.Start();
##s_node_map = amc.cam[0].GetTLStreamNodeMap()
##buffer_count = pyspin.CIntegerPtr(s_node_map.GetNode('StreamBufferCountManual'))
##handling_mode = pyspin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
##handling_mode_entry = handling_mode.GetEntryByName('OldestFirst')
##handling_mode.SetIntValue(handling_mode_entry.GetValue())


#time.sleep(0.05);
#amc.SetBinning(2);
#amc.Start();
#Img=amc.GetNextImage();
#amc.Stop();
#amc.SaveImageTimeSeries(2,'filename')
#amc.SaveImageSequenceTIFF(100,'filename');
#amc.Stop();    
#frames=amc.FramesInBuffer();
#print(frames);

    
