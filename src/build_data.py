import re, csv, json, datetime
D='/workspace/invest/patrimoine-dashboard/data/'
# 1. INSEE
s=open(D+'insee_010567059_ipla_fm_cvs.xml').read()
meta=re.search(r'<Series [^>]*LAST_UPDATE="([^"]+)"',s).group(1)
obs=[]
for m in re.finditer(r'<Obs ([^>]*)/>',s):
    a=dict(re.findall(r'(\w+)="([^"]*)"',m.group(1)))
    obs.append((a['TIME_PERIOD'],float(a['OBS_VALUE']),a.get('OBS_STATUS','')))
obs.sort()
pr=[o for o in obs if o[0]>='2001-Q1']
d={o[0]:o[1] for o in obs}
last=obs[-1]; y,q=last[0].split('-')
def ago(n): return f"{int(y)-n}-{q}"
ev={n:{'from':ago(n),'v0':d[ago(n)],'pct':round((last[1]/d[ago(n)]-1)*100,1),'cagr':round(((last[1]/d[ago(n)])**(1/n)-1)*100,2)} for n in (25,10,5)}
peak=max(obs,key=lambda o:o[1])
prix={'idbank':'010567059','last_update':meta,'series':[[o[0],o[1],o[2]] for o in pr],
 'last':{'period':last[0],'value':last[1],'status':last[2]},'ev':ev,
 'peak':{'period':peak[0],'value':peak[1],'dd':round((last[1]/peak[1]-1)*100,1)},'first_available':obs[0][0]}
# 2. Taux BdF (MIR) >10 ans fixation
r=list(csv.DictReader(open(D+'ecb_M.FR.B.A2C.P.R.A.2250.EUR.N.csv')))
ts=[[x['TIME_PERIOD'],float(x['OBS_VALUE']),x['OBS_STATUS']] for x in r if x['TIME_PERIOD']>='2001-01']
ann={}
for t,v,_ in ts: ann.setdefault(t[:4],[]).append(v)
annavg={k:round(sum(v)/len(v),2) for k,v in ann.items()}
def cost(rate,P=200000,n=300):
    i=rate/100/12; m=P*i/(1-(1+i)**-n); return round(m,2), round(m*n-P)
cl={'oct2026':3.49,'sep2026':3.40,'table':[['Décembre 2025',3.16,3.09,3.17,3.25],['Mars 2026',3.22,3.04,3.21,3.27],['Juin 2026',3.25,3.12,3.22,3.30],['Septembre 2026',3.40,3.21,3.39,3.45],['Octobre 2026',3.49,3.32,3.54,3.57]]}
yrs=['2001','2008','2012','2016','2021','2023']
sim=[]
for yy in yrs:
    m,c=cost(annavg[yy]); sim.append({'label':yy+' (moy. annuelle BdF)','rate':annavg[yy],'mens':m,'interets':c,'src':'bdf'})
m,c=cost(ts[-1][1]); sim.append({'label':'Sept. 2026 (BdF)','rate':ts[-1][1],'mens':m,'interets':c,'src':'bdf'})
m,c=cost(cl['table'][-1][4]); sim.append({'label':'Oct. 2026 (CL/CSA, prêts 25 ans)','rate':cl['table'][-1][4],'mens':m,'interets':c,'src':'cl'})
taux={'key':'MIR.M.FR.B.A2C.P.R.A.2250.EUR.N','series':ts,'annual':annavg,'last':ts[-1],'min':min(ts,key=lambda x:x[1]),'max':max(ts,key=lambda x:x[1]),'cl':cl,'sim':sim}
# 3. Trends
def rd(f):
    rows=list(csv.DictReader(open(D+f))); return rows
A=rd('trends_achat_FR_12m.csv'); V=rd('trends_vente_pivot_FR_12m.csv')
ak=["achat immobilier","acheter immobilier","acheter maison","acheter appartement"]
vk=["vente immobilier","vendre immobilier","estimation immobilière","agence immobilière"]
full=[i for i,x in enumerate(A) if x['isPartial']=='False']
pa=sum(int(A[i]['acheter maison']) for i in full); pv=sum(int(V[i]['acheter maison']) for i in full)
k=pa/pv
dates=[x['date'] for x in A]
assert dates==[x['date'] for x in V]
terms={t:[int(x[t]) for x in A] for t in ak}
terms.update({t:[round(int(x[t])*k,1) for x in V] for t in vk})
ga=[sum(terms[t][i] for t in ak) for i in range(len(dates))]
gv=[sum(terms[t][i] for t in vk) for i in range(len(dates))]
def avg(l,idx): return sum(l[i] for i in idx)/len(idx)
f12=full; f3=full[-13:]; fp=full[-26:-13]
tr={'dates':dates,'partial':[x['isPartial']=='True' for x in A],'terms':terms,'ga':[round(x,1) for x in ga],'gv':[round(x,1) for x in gv],'k':round(k,3),
 'ratio12':round(avg(ga,f12)/avg(gv,f12),2),'ratio3':round(avg(ga,f3)/avg(gv,f3),2),
 'trendA':round((avg(ga,f3)/avg(ga,fp)-1)*100,1),'trendV':round((avg(gv,f3)/avg(gv,fp)-1)*100,1),
 'retrieved':datetime.datetime.fromtimestamp(__import__('os').path.getmtime(D+'trends_achat_FR_12m.csv')).strftime('%Y-%m-%d %H:%M')}
out={'generated':datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),'prix':prix,'taux':taux,'trends':tr}
json.dump(out,open(D+'dashboard_data.json','w'),ensure_ascii=False)
print(json.dumps({'prix':{k:prix[k] for k in ('last','ev','peak','last_update')},'taux':{k:taux[k] for k in ('last','min','max')},'sim':sim,'tr':{k:tr[k] for k in ('k','ratio12','ratio3','trendA','trendV','retrieved')}},ensure_ascii=False,indent=1))
