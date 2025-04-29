from pyproj import Proj, transform # type: ignore

# inProj = Proj(init='epsg:3857') # deprecated since 2.4
# outProj = Proj(init='epsg:4326') # deprecated since 2.4
inProj = Proj('epsg:3857')  
outProj = Proj('epsg:4326') 
x1,y1 = -11705274.6374,4826473.6922
x2,y2 = transform(inProj,outProj,x1,y1) # deprecated some time later than 2.4
print (x2,y2) 