#import pyspin
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
            self.pixelformat=self.cam[0].PixelFormat();
            self.height.append(self.cam[0].SensorHeight());
            self.width.append(self.cam[0].SensorWidth());        
            self.framerate=self.cam[0].AcquisitionFrameRate();
            self.exposuretime=self.cam[0].ExposureTime();
            
            if (self.camcount > 1):
                for i in range(1,self.camcount):   #Syncing setup for follower BlackFlys.             
                    self.cam[i].TriggerMode.SetValue(pyspin.TriggerMode_Off)
                    self.cam[i].TriggerSource.SetValue(pyspin.TriggerSource_Line3)
                    self.cam[i].TriggerOverlap.SetValue(pyspin.TriggerOverlap_ReadOut)
                    self.cam[i].TriggerMode.SetValue(pyspin.TriggerMode_On)
                    self.height[i].append(self.cam[i].SensorHeight());
                    self.width[i].append(self.cam[i].SensorWidth());                    
                    self.cam[i].AcquisitionFrameRateEnable.SetValue(False)
                    self.cam[i].ExposureAuto.SetValue(False)
           
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

    def SetExposureMode(self,mode='once'):
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
        images=[]
        try:                     
                for i in range(self.camcount):                   
                   image=self.cam[i].GetNextImage(1000);
                   images.append(image.GetNDArray())
                   image.Release()
                   
        except pyspin.SpinnakerException as ex:
              print('Error: %s' % ex)
              return False;
        return images;

    def GetAllBufferedImages(self):        
        images=[]
        try:
            for j in range(self.FramesInBuffer()):
                for i in range(self.camcount):            
                   image=self.cam[i].GetNextImage(1000);
                   images.append(image.GetNDArray())
                   image.Release()
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False;
        return images;      # Return all appended images;

    def SetExposureTime(self,exposure): # in uS
        try:            
            # Set 1st Cam, others follow.
            amc.cam[0].ExposureAuto.SetValue(pyspin.ExposureAuto_Off)
            exposure = min(self.cam[0].ExposureTime.GetMax(), exposure)
            self.cam[0].ExposureTime.SetValue(exposure);
            self.exposuretime=self.cam[0].ExposureTime();
            self.framerate=self.cam[0].AcquisitionFrameRate();            
            return self.exposuretime;
        
        except pyspin.SpinnakerException as ex:
           print('Error: %s' % ex)
           return False         
        
    def SetFrameRate(self,rate): #in Hz
        try:
            # Set 1st Cam, others follow.
            self.cam[0].AcquisitionFrameRateEnable.SetValue(True)
            self.cam[0].AcquisitionFrameRate.SetValue(rate);
            self.framerate=self.cam[0].AcquisitionFrameRate();
            self.exposuretime=self.cam[0].ExposureTime();
            return self.framerate; 
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False          

    def AcquireImageSequence(self, framecount):
        try:            
            timeout=500; # Something has gone wrong at this point.
            
            for i in range(framecount):
                  for j in range(self.camcount):    
                      image=self.cam[j].GetNextImage(timeout)
                      images.append(image.GetNDArray())
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
             
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False           
        
    def SaveImageSequenceAVI(self, framecount,filename):
        try:            
            timeout=500; # Something has gone wrong at this point.
            avi_handler=[];
            avi_header_settings=[];
           # tme=int(time.time())
            for j in range(self.camcount): 
                avi_handler.append(pyspin.SpinVideo());
                avi_header_settings[j]=pyspin.AVIOption();
                avi_header_settings[j].frameRate=self.framerate;
                avi_header_settings[j].height=self.cam[j].Height();
                avi_header_settings[j].width=self.cam[j].Width();                
                filename=filename+'CAM_'+str(j)+'.avi'   
                avi_handler[j].Open(filename,avi_header_settings[j])
                
            for i in range(framecount):
                  for j in range(self.camcount):    
                      image=self.cam[j].GetNextImage()                      
                      avi_handler[j].Append(image)
                      image.Release()                                        
                        
            for j in range(self.camcount):                       
                avi_handler[j].Close()
        
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False         

    def SaveImageTimeSeriesAVI(self, time,filename): #in S
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
                avi_header_settings[j]=pyspin.AVIOption();
                avi_header_settings[j].frameRate=self.framerate;
                avi_header_settings[j].height=self.cam[j].Height();
                avi_header_settings[j].width=self.cam[j].Width();                
                filename=filename+'CAM_'+str(j)+'.avi'   
                avi_handler[j].Open(filename,avi_header_settings[j])
                
            for i in range(framecount):
                  for j in range(self.camcount):    
                      image=self.cam[j].GetNextImage()                      
                      avi_handler[j].Append(image)
                      image.Release()                            
            for j in range(self.camcount):                       
                avi_handler[j].Close()
        
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False    

    def SaveImageSequenceTIFF(self, framecount,filename): 
        from libtiff import TIFF
        from PIL import Image
        
        try:            
            timeout=500; # Something has gone wrong at this point.
            tif_handler=[];
            tif_header=[];
           # tme=int(time.time())
            for j in range(self.camcount):
                
                filename=filename+'CAM_'+str(j)+'.tiff'   
                tif_handler.append(TIFF.open(filename, mode = 'w'));                
                
            for i in range(framecount):
                  for j in range(self.camcount):
                      
                      image=self.cam[j].GetNextImage()
                      #images=image.GetNDArray()
                      im = Image.fromarray(image.GetNDArray())
                #      im = im.resize((int(self.cam[j].Width()),int(self.cam[j].Height())), Image.Resampling.LANCZOS)                        
                      tif_handler[j].write_image(im, compression = None)                      
                        
            for j in range(self.camcount):                       
                tif_handler[j].close()
        
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False

    def SaveImageTimeSeriesTIFF(self, framecount,filename): 
        from libtiff import TIFF
        from PIL import Image
        from math import ceil
        
        framecount=ceil(self.framerate*time);
        try:            
            timeout=500; # Something has gone wrong at this point.
            tif_handler=[];
            tif_header=[];
           # tme=int(time.time())
            for j in range(self.camcount):
                
                filename=filename+'CAM_'+str(j)+'.tiff'   
                tif_handler.append(TIFF.open(filename, mode = 'w'));                
                
            for i in range(framecount):
                  for j in range(self.camcount):
                      
                      image=self.cam[j].GetNextImage()
                      #images=image.GetNDArray()
                      im = Image.fromarray(image.GetNDArray())
                #      im = im.resize((int(self.cam[j].Width()),int(self.cam[j].Height())), Image.Resampling.LANCZOS)                        
                      tif_handler[j].write_image(im, compression = None)                      
                        
            for j in range(self.camcount):                       
                tif_handler[j].close()
        
        except pyspin.SpinnakerException as ex:
            print('Error: %s' % ex);
        return False    

#### Testing stuff

cams=listCams();       
amc=MultiCamObj(cams[0]); #The 2 color blackfly

#amc.Start();


#time.sleep(0.05);
#amc.SetBinning(2);
amc.Start();
#amc.SaveImageTimeSeries(2,'filename')
amc.SaveImageSequenceTIFF(100,'filename');
amc.Stop();    
#frames=amc.FramesInBuffer();
#print(frames);

    
