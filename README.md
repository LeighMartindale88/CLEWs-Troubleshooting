# CLEWs-Troubleshooting
A script designed to find basic inputting errors when creating a CLEWs model. Designed to to work with the GAMS files.  

The script works as a general error/problem checker that can take into account the idiosyncrasies of the GAMS txt data file

Its current functions are (usually for a group of specified parameters) is to flag:

   - 'zeros' after a non-zero value
   - any zero in the parameters Input Activity Ratio and Open Activty Ratio 
   - values which are outside of a certain expected range for certain parameters
   - any abrupt 5%+ change between values in rows
   - any duplicate value in rows for AAD and SAA
   - incorect spellings of technologies and commodities
