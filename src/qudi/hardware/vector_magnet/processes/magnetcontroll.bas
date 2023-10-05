'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 4
' Initial_Processdelay           = 3000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = Low
' Priority_Low_Level             = 1
' Version                        = 1
' ADbasic_Version                = 6.3.1
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DESKTOP-O5HD7AV  DESKTOP-O5HD7AV\yy3
'<Header End>
#Include ADwinGoldII.inc
Dim level_x as Long
Dim level_y as Long
Dim level_z as Long
Dim no_steps_x as Long
Dim no_steps_y as Long
Dim no_steps_z as Long
Dim index as Long

Function convert(input) As Long 
  If (AbsF(input)<10) Then     
    convert = input * 3277 + 32768 
  Else
    convert = 32768
  EndIf
EndFunction

Function convert_back(input) As Float     
  convert_back = (input-32768)/3277 
EndFunction
  
Init:
  
Event: 
   
  level_x = ADC(1)
  level_y = ADC(2)
  level_z = ADC(3)
  no_steps_x = Abs(level_x - convert(FPAR_1))
  no_steps_y = Abs(level_y - convert(FPAR_2))
  no_steps_z = Abs(level_z - convert(FPAR_3))

  
  For index = 1 To 75
    
    If ((level_x + 75) < convert(FPAR_1)) Then
      DAC(4, level_x+index)
    EndIf
    
    If ((level_x - 75) > convert(FPAR_1)) Then
      DAC(4, level_x-index)
    EndIf

    If ((level_y + 75) < convert(FPAR_2)) Then
      DAC(5, level_y+index)
    EndIf
    
    If ((level_y - 75) > convert(FPAR_2)) Then
      DAC(5, level_y-index)
    EndIf
    
    If ((level_z + 75) < convert(FPAR_3)) Then
      DAC(6, level_z+index)
    EndIf
    
    If ((level_z - 75) > convert(FPAR_3)) Then
      DAC(6, level_z-index)
    EndIf
    
    FPAR_4 = convert_back(ADC(1))
    FPAR_5 = convert_back(ADC(2))
    FPAR_6 = convert_back(ADC(3))
    CPU_Sleep(100000)
    
  Next
  
  If (((no_steps_x < 100) AND (no_steps_y < 100)) AND (no_steps_z < 100)) Then
    End
  EndIf
Finish:
  DAC(4, convert(FPAR_1))
  DAC(5, convert(FPAR_2))
  DAC(6, convert(FPAR_3))
  FPAR_4 = convert_back(ADC(1))
  FPAR_5 = convert_back(ADC(2))
  FPAR_6 = convert_back(ADC(3))
