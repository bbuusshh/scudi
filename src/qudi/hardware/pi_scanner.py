import ctypes
import time

import numpy

import nidaqcpp


class PIScanner:  # (MultiBoard):#(BufferedCounting):

    PIDll = ctypes.windll.LoadLibrary("PI_GCS2_Dll.dll")
    c_double_p = ctypes.POINTER(ctypes.c_double)

    def CheckError(self):
        iError = self.PIDll.PI_GetError(self.ID)
        buf_size = ctypes.c_long(1024)
        szErrorMesage = ctypes.create_string_buffer("\000" * buf_size.value)
        self.PIDll.PI_TranslateError(iError, szErrorMesage, buf_size)
        return szErrorMesage.value

    def connect(self):
        # getting the description string of the controller
        buf_size = ctypes.c_long(1024)
        szUsbController = ctypes.create_string_buffer("\000" * buf_size.value)
        szFilter = ctypes.c_char_p("PI E-712")
        self.PIDll.PI_EnumerateUSB(
            szUsbController, buf_size, szFilter
        )  # lists the identification string of all controllers available via USB interface

        # connecting to the controller
        self.ID = self.PIDll.PI_ConnectUSB(szUsbController)
        if self.ID < 0:
            print self.CheckError()
        print "usb: ", szUsbController.value

    def getAxes(self):
        iBufferSize = 16
        self.szAxes = ctypes.create_string_buffer("\000" * (iBufferSize + 1))
        if not self.PIDll.PI_qSAI(self.ID, self.szAxes, iBufferSize):  # geting the list of axis identifier
            print self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        print "szaxes: ", self.szAxes.value

    def Servo(self, switch):
        boolarray1 = ctypes.c_bool * 1
        bFlags = boolarray1(switch)
        ax = ctypes.create_string_buffer("1")
        if not self.PIDll.PI_SVO(self.ID, ax, bFlags):
            print self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        ax = ctypes.create_string_buffer("2")
        if not self.PIDll.PI_SVO(self.ID, ax, bFlags):
            print self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        ax = ctypes.create_string_buffer("3")
        if not self.PIDll.PI_SVO(self.ID, ax, bFlags):
            print self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

    # def Servo(self , switch ):
    #    boolarray3 = ctypes.c_bool * 3
    #    bFlags = boolarray3(switch, switch, switch)
    #    print bFlags[0], bFlags[1], bFlags[2]
    #    print "szaxes: ", self.szAxes.value
    #    if ( not self.PIDll.PI_SVO(self.ID, self.szAxes, bFlags) ):
    #        print self.CheckError()
    #        self.PIDll.PI_CloseConnection(self.ID)
    #    bFlags = boolarray3(False, False, False)
    #    if (not self.PIDll.PI_qSVO(self.ID, self.szAxes,  bFlags)):
    #        print self.CheckError()
    #        self.PIDll.PI_CloseConnection(self.ID)
    #    print bFlags[0], bFlags[1], bFlags[2]
    #

    def getservotime(self):
        uintarray1 = ctypes.c_uint * 1
        iParameterArray = uintarray1(
            234881536
        )  # = 0x0E000200 ; parameter which indicate servo update time of the controller
        # pdValueArray = self.c_double_p() # array to receive the value of the requested parameters
        cdoubleArray = ctypes.c_double * 2
        pdValueArray = cdoubleArray()
        iMaxNameSize = 300
        szStrings = ctypes.create_string_buffer("\000" * (iMaxNameSize + 1))  # buffer to store the GCS array header
        szAxes0 = ctypes.create_string_buffer("1")  # string wigh designators
        if not self.PIDll.PI_qSPA(self.ID, szAxes0, iParameterArray, pdValueArray, szStrings, iMaxNameSize):
            print "er ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

        self.servotime = pdValueArray[0]

    def getlimits(self):
        cdoubleArray = ctypes.c_double * 3
        pdValueArraymin = cdoubleArray()
        pdValueArraymax = cdoubleArray()
        if not self.PIDll.PI_qTMN(self.ID, self.szAxes, pdValueArraymin):
            print self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        if not self.PIDll.PI_qTMX(self.ID, self.szAxes, pdValueArraymax):
            print self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

        self.xRange = (pdValueArraymin[0], pdValueArraymax[0])
        self.yRange = (pdValueArraymin[1], pdValueArraymax[1])
        self.zRange = (pdValueArraymin[2], pdValueArraymax[2])

    def __init__(
        self,
        CounterIn,
        CounterOut,
        TickSource,
        AOChannels,
        x_range=(0.0, 100.0),
        y_range=(0.0, 100.0),
        z_range=(-10.0, 10.0),
        v_range=(0.0, 10.0),
        invert_x=False,
        invert_y=False,
        invert_z=False,
        swap_xy=False,
        TriggerChannels=None,
    ):
        self.case = 2
        if self.case == 0:
            xx = 0

            # CounterBoard.__init__(self, CounterIn, CounterOut, TickSource)
            # MultiBoard.__init__(self, CounterIn=CounterIn,
        #                          CounterOut=CounterOut,
        #                          TickSource=TickSource,
        #                          AOChannels=AOChannels,
        #                          v_range=v_range)
        elif self.case == 1:
            xx = 1
            # BufferedCounting.__init__(self, CounterIn, CounterOut)
        elif self.case == 2:
            self.clockRate = 0.1
            self.clock = nidaqcpp.PulseGenerator(CounterOut, self.clockRate, 0.5)
            pixelclock = CounterOut + "InternalOutput"
            self.NumOfPoint = 10
            self.counter = nidaqcpp.BufferedCounting(CounterIn, TickSource, pixelclock, self.NumOfPoint, self.clockRate)
        elif self.case == 3:
            self.clockRate = 0.1
            # self.clock = nidaqcpp.PulseGenerator(CounterOut, self.clockRate, .5)
            pixelclock = "/Dev1/PFI0"
            self.NumOfPoint = 10
            self.counter = nidaqcpp.BufferedCounting(CounterIn, TickSource, pixelclock, self.NumOfPoint, self.clockRate)
        elif self.case == 4:
            self.clockRate = 0.1
            # self.clock = nidaqcpp.PulseGenerator(CounterOut, self.clockRate, .5)
            pixelclock = "/Dev1/PFI0"
            self.NumOfPoint = 10
            self.counter = nidaqcpp.BufferedCounting(CounterIn, TickSource, pixelclock, self.NumOfPoint, self.clockRate)
            self.countPulseWidth = nidaqcpp.BufferedPulseWidth(CounterOut, "/Dev1/80MHzTimebase", "/Dev1/PFI0", 2000)
        elif self.case == 5:
            self.clockRate = 0.1
            # self.clock = nidaqcpp.PulseGenerator(CounterOut, self.clockRate, .5)
            pixelclock = "/Dev1/PFI0"
            self.NumOfPoint = 10
            self.counter = nidaqcpp.BufferedCounting(CounterIn, TickSource, pixelclock, self.NumOfPoint, self.clockRate)
            self.countPulseWidth = nidaqcpp.BufferedCounting(
                CounterOut,
                "/Dev1/80MHzTimebase",
                pixelclock,
                self.NumOfPoint,
                self.clockRate,
            )

        if TriggerChannels is not None:
            self._trigger_task = DOTask(TriggerChannels)
        self.vRange = v_range
        self.invert_x = invert_x
        self.invert_y = invert_y
        self.invert_z = invert_z
        self.swap_xy = swap_xy
        #########################
        self.connect()
        self.getAxes()
        self.Servo(True)
        self.getservotime()

        ##########################################
        ##########################################
        # self.xRange = x_range
        # self.yRange = y_range
        # self.zRange = z_range
        self.getlimits()

        # self.vRange = v_range

        # self.x = 0.0
        # self.y = 0.0
        # self.z = 0.0
        self.getpos()

        # self.invert_x = invert_x
        # self.invert_y = invert_y
        # self.invert_z = invert_z
        # self.swap_xy = swap_xy

        # initial values for the wave
        self.Amp = 0
        # self.NumOfPoint= 0
        self.AxisId = 0
        self.Rate = 0
        self.time_tagger = CounterIn

    def getXRange(self):
        return self.xRange

    def getYRange(self):
        return self.yRange

    def getZRange(self):
        return self.zRange

    def setx(self, x):
        self.setPosition(x, self.y, self.z)

    def sety(self, y):
        self.setPosition(self.x, y, self.z)

    def setz(self, z):
        self.setPosition(self.x, self.y, z)

    def getpos(self):
        doublearray3 = ctypes.c_double * 3
        dPos = doublearray3()
        self.PIDll.PI_qPOS(self.ID, self.szAxes, dPos)
        self.x, self.y, self.z = dPos[0], dPos[1], dPos[2]
        return self.x, self.y, self.z

    def setPosition(self, x, y, z):
        doublearray3 = ctypes.c_double * 3
        dPos = doublearray3(x, y, z)
        szAxes00 = ctypes.create_string_buffer("1")
        if not self.PIDll.PI_MOV(self.ID, self.szAxes, dPos):
            print self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

        # Read the moving state of the axes#
        boolarray3 = ctypes.c_bool * 3
        pbValueArray = boolarray3()
        # if 'pbValueArray[0]' = TRUE at least one axis of the controller is still moving.
        # if 'pbValueArray[0]' = FALSE no axis of the contrller is moving.
        szAxes0 = ctypes.create_string_buffer(
            ""
        )  # if 'axes' = NULL or 'axis' is empty a general moving state of all axes ist returnd in 'bIsMoving[0]'
        pbValueArray[0] = True
        while pbValueArray[0]:
            if not self.PIDll.PI_IsMoving(self.ID, None, pbValueArray):
                print self.CheckError()
                self.PIDll.PI_CloseConnection(self.ID)
                pbValueArray[0] = False

        self.getpos()

    def scanLine_position(self, start, stop, axisId, N, SecondsPerPoint, type="lin"):
        self.setPosition(start[0], start[1], start[2])  # self.setPosition(Line[0][0],Line[1][0],Line[2][0])
        amp = stop - start[axisId - 1]

        mod = 257

        con = False
        sudp = 0
        rate = int(round(SecondsPerPoint / self.servotime))
        # print "rate = ", rate
        numofpoints = N  # * rate/r
        N2 = N + 2 * sudp / rate
        if self.Amp != amp or self.NumOfPoint != numofpoints:
            self.CreateWave(amp, numofpoints, type, sudp)
            con = True
        if self.AxisId != axisId:
            self.DataRecConfig(axisId)
            con = True
        if self.Rate != rate:
            self.SetWavGenRate(rate)
            self.SetRecRate(rate)
        if con:
            self.ConWavGen(axisId)

        self.setOffset(start[axisId - 1])  # self.setOffset(min)

        self.WavGen(mod)
        iArraySize = 3
        boolarray3 = ctypes.c_bool * iArraySize
        pbValueArray = boolarray3()
        # if 'pbValueArray[0]' = TRUE corresponding wavegenerator is running False: is not running

        pbValueArray[0] = True
        s = (N2 - 2) * SecondsPerPoint
        sleeptime = (N2 - 2) * SecondsPerPoint
        time.sleep(sleeptime)
        while pbValueArray[0]:
            time.sleep(0.00001)
            if not self.PIDll.PI_IsGeneratorRunning(self.ID, None, pbValueArray, iArraySize):
                print self.CheckError()
                self.PIDll.PI_CloseConnection(self.ID)
        positions = self.ReadRecData(N2)

        return positions

    def scanLine(self, start, stop, axisId, N, SecondsPerPoint, type="lin"):
        """Perform a line scan. If return_speed is not None, return to beginning of line
        with a speed 'return_speed' times faster than the speed currently set.
        """

        start0 = start[axisId - 1]
        step = (stop - start0 + 0.0) / (N)
        looptimes = 1
        if self.case == 3 or self.case == 4 or self.case == 5:
            if type == "ramp":
                if N % 2 != 0:
                    raise RuntimeError("scanline failed: for type = ramp N should be even")
                N = N / 2
                looptimes = 2
                type = "lin"
            if axisId == 1:
                range_ = self.getXRange()
            elif axisId == 2:
                range_ = self.getYRange()
            elif axisId == 3:
                range_ = self.getZRange()
            if start0 < stop:
                noffsetstart = min(4, (start0 - range_[0]) / step)
                noffsetstop = min(4, (range_[1] - stop) / step)
            else:
                noffsetstart = min(4, (start0 - range_[1]) / step)
                noffsetstop = min(4, (range_[0] - stop) / step)
            noffsetstart = int(noffsetstart)
            noffsetstop = int(noffsetstop)
            if self.case == 4 or self.case == 5:
                width = numpy.array([], dtype=numpy.uint32)
        else:
            noffsetstart = 0
            noffsetstop = 0
        data = numpy.array([], dtype=numpy.uint32)
        for i in range(looptimes):
            if i == 1:
                start0, stop = stop, start0
                noffsetstart, noffsetstop = noffsetstop, noffsetstart
                step = (stop - start0 + 0.0) / (N)
            waveStart0 = start0 - noffsetstart * step
            waveStop = stop + noffsetstop * step
            start[axisId - 1] = waveStart0

            amp = waveStop - waveStart0
            self.setPosition(start[0], start[1], start[2])  # self.setPosition(Line[0][0],Line[1][0],Line[2][0])
            # dim = Line.shape[0]
            # N = Line.shape[1]
            # if dim is not 3:
            #   return
            # difx = Line[0][N-1]-Line[0][0]
            # dify = Line[1][N-1]-Line[1][0]
            # difz = Line[2][N-1]-Line[2][0]
            # if ( difx == 0 and dify==0 ):
            #    axisId = 3
            # elif ( difx == 0 and difz==0):
            #    axisId = 2
            # elif (dify==0 and difz==0):
            #     axisId= 1
            #  else:
            #       return

            # min = Line[axisId-1][0]
            # max = Line[axisId-1][N-1]
            # amp = max - min
            # if return_speed is None:
            #   mod=257
            # else:
            #    mod=1
            # if (return_):
            #    mod = 1
            # else:
            #    mod = 257

            mod = 257
            con = False
            sudp = 0

            rate = int(round(SecondsPerPoint / self.servotime))
            numofpoints = N + noffsetstart + noffsetstop  # * rate

            if self.Amp != amp or self.NumOfPoint != numofpoints:
                self.CreateWave(amp, numofpoints, type, sudp)
                con = True
            if self.AxisId != axisId:
                # self.DataRecConfig(axisId)
                con = True
            # rate = int(round(SecondsPerPoint/self.servotime))
            # secperpoint=rate*self.servotime
            if self.Rate != rate:
                self.SetWavGenRate(rate)
                self.SetRecRate(rate)
            if con:
                self.ConWavGen(axisId)
            self.setOffset(waveStart0)  # self.setOffset(min)

            ########self.setTiming(SecondsPerPoint*0.1, SecondsPerPoint*0.9)

            # if self.AOLength() != N: # set buffers of nidaq Tasks, data read buffer and timeout if needed
            #   self.setAOLength(N)
            f = 1.0 / SecondsPerPoint

            if self.case == 0:
                self.setTiming(SecondsPerPoint * 0.1, SecondsPerPoint * 0.9)
                if self.CountLength() != N + 1:
                    self.setCountLength(N + 1)
            elif self.case == 1:
                if self.Rate0() != f:
                    self.setTiming(SecondsPerPoint)
                if self.CountLength() != N + 1:
                    self.setCountLength(N + 1)
            elif self.case == 2:
                self.clock.setFreq(f)
                if self.counter.readLength() != N + 1 or self.counter.samplingRate() != f:
                    self.counter.setLength(N + 1, f)
            elif self.case == 3:
                if self.counter.readLength() != N + 1 or self.counter.samplingRate() != f:
                    self.counter.setLength(N + 1, f)
            elif self.case == 4:
                if self.counter.readLength() != N + 1 or self.counter.samplingRate() != f:
                    self.counter.setLength(N + 1, f)
                    self.countPulseWidth.setLength(N)
            elif self.case == 5:
                if self.counter.readLength() != N + 1 or self.counter.samplingRate() != f:
                    self.counter.setLength(N + 1, f)
                    self.countPulseWidth.setLength(N + 1, f)
            ###

            # send line start trigger
            if hasattr(self, "_trigger_task"):
                self._trigger_task.Write(numpy.array((1, 0), dtype=numpy.uint8))
                time.sleep(0.001)
                self._trigger_task.Write(numpy.array((0, 0), dtype=numpy.uint8))

            # acquire line
            # self.WriteAO( self.PosToVolt(Line) )
            if self.case == 0 or self.case == 1:
                self.StartCI()
                self.StartCO()
            elif self.case == 2:
                self.counter.Start()
                self.clock.Start()
            elif self.case == 3:
                self.counter.Start()
            elif self.case == 4 or self.case == 5:
                self.counter.Start()
                self.countPulseWidth.Start()
            # if (axisId==3):
            #   time.sleep(0.2)
            # if (self.case ==3 or self.case==4or self.case==5):
            self.TrigSet2(start0, stop + step / 2, abs(step))
            self.WavGen(mod)
            # self.StartAO()
            # Checking if wave generators are running #
            iArraySize = 3
            boolarray3 = ctypes.c_bool * iArraySize
            pbValueArray = boolarray3()
            # if 'pbValueArray[0]' = TRUE corresponding wavegenerator is running False: is not running

            pbValueArray[0] = True
            s = (N - 2) * SecondsPerPoint
            sleeptime = (N - 2) * SecondsPerPoint
            time.sleep(sleeptime)
            while pbValueArray[0]:
                time.sleep(0.00001)
                if not self.PIDll.PI_IsGeneratorRunning(self.ID, None, pbValueArray, iArraySize):
                    print self.CheckError()
                    self.PIDll.PI_CloseConnection(self.ID)

            # self.WaitCI()

            # send line stop trigger
            if hasattr(self, "_trigger_task"):
                self._trigger_task.Write(numpy.array((0, 1), dtype=numpy.uint8))
                time.sleep(0.001)
                self._trigger_task.Write(numpy.array((0, 0), dtype=numpy.uint8))

            if self.case == 0 or self.case == 1:
                data = self.ReadCI()
                # self.StopAO()
                self.StopCI()
                self.StopCO()
            elif self.case == 2:
                data = numpy.concatenate((data, self.counter.readArray()))
                self.counter.Stop()
                self.clock.Stop()
            elif self.case == 3:
                data = numpy.concatenate((data, self.counter.readArray()))
                self.counter.Stop()
            elif self.case == 4 or self.case == 5:
                data = numpy.concatenate((data, self.counter.readArray()))
                width = numpy.concatenate((width, self.countPulseWidth.readArray()))
                # print 'data =  ',data
                print "width=  ", width
                self.counter.Stop()
                self.countPulseWidth.Stop()

            # self.ReadRecData()

            # if return_speed is not None:
            #   self.setTiming(SecondsPerPoint*0.5/return_speed, SecondsPerPoint*0.5/return_speed)
            # self.WriteAO( self.PosToVolt(Line[:,::-1]) )
            # self.StartAO()
            #  self.StartCI()
            # self.StartCO()
            # self.WaitCI()
            # self.StopAO()
            # self.StopCI()
            # self.StopCO()
            # self.setTiming(SecondsPerPoint*0.1, SecondsPerPoint*0.9)
        # res=data[1:]*(4e7/width)

        if self.case == 0 or self.case == 1:
            return data[1:] * self._f / self._DutyCycle
        elif self.case == 2 or self.case == 3:
            return data[1:] * f
        elif self.case == 4:
            return data[1:] * (4e7 / width)
        elif self.case == 5:
            return data[1:] * (8e7 / width[1:])

    def scanLinetimetagger(self, Line, SecondsPerPoint, return_speed=None):
        """Perform a line scan. If return_speed is not None, return to beginning of line
        with a speed 'return_speed' times faster than the speed currently set.
        """
        dim = Line.shape[0]
        N = Line.shape[1]
        if dim is not 3:
            return
        difx = Line[0][N - 1] - Line[0][0]
        dify = Line[1][N - 1] - Line[1][0]
        difz = Line[2][N - 1] - Line[2][0]
        if difx == 0 and dify == 0:
            axisId = 3
        elif difx == 0 and difz == 0:
            axisId = 2
        elif dify == 0 and difz == 0:
            axisId = 1
        else:
            return

        min = Line[axisId - 1][0]
        max = Line[axisId - 1][N - 1]
        amp = max - min
        if return_speed is None:
            mod = 257
        else:
            mod = 1

        con = False
        if self.Amp != amp or self.NumOfPoint != N:
            self.CreateWave(amp, N)
            con = True
        if self.AxisId != axisId:
            # self.DataRecConfig(axisId)
            con = True
        rate = int(round(SecondsPerPoint / self.servotime))
        secperpoint = rate * self.servotime
        if self.Rate != rate:
            self.SetWavGenRate(rate)
        if con:
            self.ConWavGen(axisId)

        self.setPosition(Line[0][0], Line[1][0], Line[2][0])
        self.setOffset(min)
        counter_0 = self.time_tagger.Counter(
            0, int(secperpoint * 1e12), N
        )  # timebin for count in channel 0(APD1) is 30*0.1 = 3 second
        counter_1 = self.time_tagger.Counter(1, int(secperpoint * 1e12), N)
        tottime = secperpoint * (N)
        counter_0.stop()
        counter_1.stop()
        counter_0.clear()
        counter_1.clear()
        self.WavGen(mod)
        counter_0.start()
        counter_1.start()
        # Checking if wave generators are running #
        iArraySize = 3
        boolarray3 = ctypes.c_bool * iArraySize
        pbValueArray = boolarray3()
        # if 'pbValueArray[0]' = TRUE corresponding wavegenerator is running False: is not running

        pbValueArray[0] = True
        while pbValueArray[0]:
            time.sleep(0.01)
            if not self.PIDll.PI_IsGeneratorRunning(self.ID, None, pbValueArray, iArraySize):
                print self.CheckError()
                self.PIDll.PI_CloseConnection(self.ID)
        # self.ReadRecData()
        # time.sleep(tottime)
        counter_0.stop()
        counter_1.stop()
        c0 = counter_0.getData()
        c1 = counter_1.getData()
        # print c0
        # print c1
        return (c1 + c0) / secperpoint

    def CreateWave(self, amp, numofpoint, type, sudp):  # write a ramp wave to the wave table 1
        self.iWaveTableId = ctypes.c_int(2)
        iOffsetOfFirstPointInWaveTable = ctypes.c_int(0)
        iNumberOfPoints = numofpoint + 2 * sudp
        iAddAppendWave = ctypes.c_int(0)  # clear the wave table and starts writing with the first point in the table
        iCenterPointOfWave = ctypes.c_int(iNumberOfPoints / 2)
        iNumberOfSpeedUpDownPointsInWave = ctypes.c_int(sudp)
        dAmplitudeOfWave = ctypes.c_double(amp)
        dOffsetOfWave = ctypes.c_double(0)
        iSegmentLength = ctypes.c_int(iNumberOfPoints)

        if type == "ramp":
            bok = self.PIDll.PI_WAV_RAMP(
                self.ID,
                self.iWaveTableId,
                iOffsetOfFirstPointInWaveTable,
                iNumberOfPoints,
                iAddAppendWave,
                iCenterPointOfWave,
                iNumberOfSpeedUpDownPointsInWave,
                dAmplitudeOfWave,
                dOffsetOfWave,
                iSegmentLength,
            )
        else:
            bok = self.PIDll.PI_WAV_LIN(
                self.ID,
                self.iWaveTableId,
                iOffsetOfFirstPointInWaveTable,
                iNumberOfPoints,
                iAddAppendWave,
                iNumberOfSpeedUpDownPointsInWave,
                dAmplitudeOfWave,
                dOffsetOfWave,
                iSegmentLength,
            )
        # bok = self.PIDll.PI_WAV_SIN_P(self.ID, self.iWaveTableId, iOffsetOfFirstPointInWaveTable, self.iNumberOfPoints, iAddAppendWave, iCenterPointOfWave, dAmplitudeOfWave, dOffsetOfWave, iSegmentLength);
        if not bok:
            print "create wave: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        else:
            self.Amp = amp
            self.NumOfPoint = iNumberOfPoints

    def DataRecConfig(self, axisId):
        intarray1 = ctypes.c_int * 1
        piRecOptionArray = intarray1(2)  # real position (record source = axis)
        szRecSourceIds = ctypes.c_char(str(axisId))
        self.piRecTableIdsArray = intarray1(1)  # ID of the record table
        if not self.PIDll.PI_DRC(
            self.ID,
            self.piRecTableIdsArray,
            ctypes.byref(szRecSourceIds),
            piRecOptionArray,
        ):  # set data record configuration
            print "data recording: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        else:
            self.AxisId = axisId

    def DataRecParams(self):
        iBufferSize = 3000
        szBuffer = ctypes.create_string_buffer("\000" * (iBufferSize + 1))
        if not self.PIDll.PI_qHDR(self.ID, szBuffer, iBufferSize):  # set data record configuration
            print "getting parameters: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        print "params = ", szBuffer.value

    def ReadRecData(self, iNumberOfValues):
        iNumberOfRecChannels = 1
        iOffsetOfFirstPointInRecordTable = 1  # index of first value to read (starts with index 1)
        # iNumberOfValues = self.NumberOfPoints # number of values to read
        pdValueArray = self.c_double_p()  # internal array to store the data of all tables
        iGcsArrayHeaderMaxSize = 300
        szGcsArrayHeader = ctypes.create_string_buffer(
            "\000" * (iGcsArrayHeaderMaxSize + 1)
        )  # buffer to store the GCS array header
        bOK = self.PIDll.PI_qDRR(
            self.ID,
            self.piRecTableIdsArray,
            iNumberOfRecChannels,
            iOffsetOfFirstPointInRecordTable,
            iNumberOfValues,
            ctypes.byref(pdValueArray),
            szGcsArrayHeader,
            iGcsArrayHeaderMaxSize,
        )  # read recorded data table asynchronously, it will return as soon as the data header has been read and start a bachground process which reads in the data itself
        if not bOK:
            print "read recording data: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

        iOldIndex = -2
        iIndex = -1
        stoptime = 1 + self.Rate * self.servotime
        # print "stoptime= ", stoptime
        while iOldIndex < iIndex:  # wait until the read pointer does not increase any more.
            iOldIndex = iIndex
            time.sleep(stoptime)
            iIndex = self.PIDll.PI_GetAsyncBufferIndex(self.ID)
        filename = "C:\\tmp\\test.dat" + str(self.x + self.y)
        # print pdValueArray[0]
        a = numpy.ctypeslib.as_array(pdValueArray, shape=(iOldIndex / iNumberOfRecChannels, iNumberOfRecChannels))
        numpy.savetxt(filename, a, fmt="%f10", delimiter=",")
        # for iIndex in range(0, iOldIndex/iNumberOfRecChannels):
        #    for k in range (0,iNumberOfRecChannels):
        #       print "iIndex = ", iIndex , " data = ",pdValueArray[(iIndex * iNumberOfRecChannels) + k]

        return a

    def SetRecRate(self, rate):
        bOK = self.PIDll.PI_RTR(
            self.ID, rate
        )  # read recorded data table asynchronously, it will return as soon as the data header has been read and start a bachground process which reads in the data itself
        if not bOK:
            print "set recording rate: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

    def SetWavGenRate(self, rate):
        iArraySize = 2
        intarray1 = ctypes.c_int * iArraySize
        piTableRateArray = intarray1(rate)
        piInterpolationTypeArray = intarray1(
            1
        )  # apply interpolation to the wave generator output between wave table points 0 = no interpolation , 1= straight line
        piWavGenIdsArr = intarray1(
            0
        )  # the wave generator ID must  be zero which means that all wave generators are selected
        if not self.PIDll.PI_WTR(
            self.ID,
            piWavGenIdsArr,
            piTableRateArray,
            piInterpolationTypeArray,
            iArraySize,
        ):
            print "set wave rate: ", rate, self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        else:
            self.Rate = rate

    def offset(self):
        iArraySize = 1
        doubleArray1 = ctypes.c_double * iArraySize
        pdValueArray = doubleArray1()
        if not self.PIDll.PI_qWOS(self.ID, self.piWaveGeneratorIdsArray, pdValueArray, iArraySize):
            print "getting offset: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

        return pdValueArray[0]

    def setOffset(self, offset):
        iArraySize = 1
        doubleArray1 = ctypes.c_double * iArraySize
        pdValueArray = doubleArray1(offset)
        if not self.PIDll.PI_WOS(self.ID, self.piWaveGeneratorIdsArray, pdValueArray, iArraySize):
            print "setting offset: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

    def ConWavGen(self, axis):
        iArraySize = 1
        intarray1 = ctypes.c_int * iArraySize
        piWaveTableIdsArray = intarray1(self.iWaveTableId)
        self.piWaveGeneratorIdsArray = intarray1(axis)
        if not self.PIDll.PI_WSL(
            self.ID, self.piWaveGeneratorIdsArray, piWaveTableIdsArray, iArraySize
        ):  # connect (disconnect) the wave generator to the wave table (assign the waveform to the axis )
            print "wave generator connection: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        piNumberOfCyclesArray = intarray1(1)
        if not self.PIDll.PI_WGC(
            self.ID, self.piWaveGeneratorIdsArray, piNumberOfCyclesArray, iArraySize
        ):  # set the number of cycles for the wave generator output
            print "setting the number of cycles of wave generator: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        else:
            self.AxisId = axis

    def WavGen(self, mod):
        # mod = 1; start wave generator output immediately, synchronized by servo cycle
        # mod = 0; wave generator output is stopped
        # mod = 256 ,0x100, bit 8: wave generator start at the endpoint of the last cycle / it should always be combined with one of the start modes bit 0 or bit 1 ---> 256 or 257
        iArraySize = 1
        intarray1 = ctypes.c_int * iArraySize
        iStartModArray = intarray1(mod)  # start wave generator output immediately, synchronized by servo cycle
        if not self.PIDll.PI_WGO(
            self.ID, self.piWaveGeneratorIdsArray, iStartModArray, iArraySize
        ):  # start the wave generator output and hence the motion of the axis
            print "start the wave generator acording the mod: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

    def TrigSet2(self, start, stop, step):
        iArraySize = 5
        doublearray5 = ctypes.c_double * iArraySize
        intarray5 = ctypes.c_int * iArraySize

        axispar = 2
        axis = self.AxisId

        trigmodppar = 3
        trigmod = 0  # position distance

        steppar = 1
        startpar = 8
        stoppar = 9

        Outputline = 1

        piTriggerOutputIdsArray = intarray5(Outputline, Outputline, Outputline, Outputline, Outputline)
        piTriggerParameterArray = intarray5(axispar, trigmodppar, steppar, startpar, stoppar)
        pdValueArray = doublearray5(axis, trigmod, step, start, stop)
        if not self.PIDll.PI_CTO(
            self.ID,
            piTriggerOutputIdsArray,
            piTriggerParameterArray,
            pdValueArray,
            iArraySize,
        ):
            print "Configuration trigger actions: ", self.CheckError(), " start = ", start, " stop = ", stop, " step = ", step
            self.PIDll.PI_CloseConnection(self.ID)
            raise RuntimeError("trigset2 call failed with error")
            # raise RuntimeError('nidaq call failed with error %d: %s'%(err,repr(buf.value)))

    def TrigSet(self):
        if not self.PIDll.PI_TWC(self.ID):
            print "Clear out trigger: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)
        iArraySize = 1
        intarray1 = ctypes.c_int * iArraySize
        piTriggerChannelIdsArray = intarray1(1)
        piPointNumberArray = intarray1(10)
        piSwitchArray = intarray1(1)

        if not self.PIDll.PI_TWS(
            self.ID,
            piTriggerChannelIdsArray,
            piPointNumberArray,
            piSwitchArray,
            iArraySize,
        ):
            print "Set trigger actions: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

        iArraySize2 = 1
        doublearray12 = ctypes.c_double * iArraySize2
        intarray12 = ctypes.c_int * iArraySize2
        piTriggerOutputIdsArray = intarray12(1)
        piTriggerParameterArray = intarray12(3)
        pdValueArray = doublearray12(4)
        if not self.PIDll.PI_CTO(
            self.ID,
            piTriggerOutputIdsArray,
            piTriggerParameterArray,
            pdValueArray,
            iArraySize2,
        ):
            print "Configuration trigger actions: ", self.CheckError()
            self.PIDll.PI_CloseConnection(self.ID)

    def PosToVolt(self, r):
        x = self.xRange
        y = self.yRange
        z = self.zRange
        v = self.vRange
        v0 = v[0]
        dv = v[1] - v[0]
        if self.invert_x:
            vx = v0 + (x[1] - r[0]) / (x[1] - x[0]) * dv
        else:
            vx = v0 + (r[0] - x[0]) / (x[1] - x[0]) * dv
        if self.invert_y:
            vy = v0 + (y[1] - r[1]) / (y[1] - y[0]) * dv
        else:
            vy = v0 + (r[1] - y[0]) / (y[1] - y[0]) * dv
        if self.invert_z:
            vz = v0 + (z[1] - r[2]) / (z[1] - z[0]) * dv
        else:
            vz = v0 + (r[2] - z[0]) / (z[1] - z[0]) * dv
        if self.swap_xy:
            vt = vx
            vx = vy
            vy = vt
        return numpy.vstack((vx, vy, vz))

    def test(self, axisId, amp, offset, numofpoint, rate):
        self.CreateWave(amp, numofpoint, "line", 0)
        self.DataRecConfig(axisId)
        self.SetWavGenRate(rate)
        self.ConWavGen(axisId)
        self.WavGen(257)
        A = self.ReadRecData(numofpoint * rate)
        print A
        # self.WavGen(0)
        # self.PIDll.PI_CloseConnection(self.ID)
