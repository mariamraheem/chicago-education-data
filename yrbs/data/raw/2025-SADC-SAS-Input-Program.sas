/****************************************************************************************/
/*  This SAS program reads ASCII format (text format) 2025 SADC data and creates a      */
/*  formatted and labeled SAS dataset.                                                  */
/*                                                                                      */
/*  Change the file location specifications from 'c:\sadc2025' to the location where    */
/*  you downloaded, unzipped, and stored the YRBS ASCII data file and the format        */
/*  library before you run this program.  Change the location specification in three    */
/*  places - in the 'filename' statement and in the two 'libname' statements at the     */
/*  top of the program.                                                                 */
/*                                                                                      */
/*  Change 'xxxxxxx' in the 'filename' statement and the 'data' statement to            */
/*  'national', 'district', 'state_a_d', 'state_e_h', 'state_i_l', 'state_m',           */
/*  'state_n_p','state_q_t', or 'state_u_z' depending on which file you are analyzing.  */
/*                                                                                      */
/*  Note: Run '2025 SADC SAS Formats Program.sas' BEFORE you run                        */
/*  '2025 SADC SAS Input Program.sas' to create the 2025SADC dataset.                   */
/****************************************************************************************/
 
filename datain 'c:\sadc2025\sadc_2025_xxxxxxx.dat';
libname dataout 'c:\sadc2025';
libname library 'c:\sadc2025';
data dataout.sadc_2025_xxxxxxx;
infile datain lrecl=900;
input
sitecode $ 1-5
sitename $ 6-55
sitetype $ 56-105
sitetypenum 106-113
year 114-121
survyear 122-124
weight 125-134
stratum 135-142
PSU 143-150
record 151-158
age 159-161
sex 162-164
grade 165-167
race4 168-170
race7 171-173
stheight 174-181
stweight 182-189
bmi 190-197
bmipct 198-205
qnobese 206-208
qnowt 209-211
q63 $ 212-212
q62 $ 213-213
q61 $ 214-214
sexid 215-222
sexid2 223-230
sexpart 231-238
sexpart2 239-246
q7 $ 247-247
q8 $ 248-248
q9 $ 249-249
q10 $ 250-250
q11 $ 251-251
q12 $ 252-252
q13 $ 253-253
q14 $ 254-254
q15 $ 255-255
q16 $ 256-256
q17 $ 257-257
q18 $ 258-258
q19 $ 259-259
q20 $ 260-260
q21 $ 261-261
q22 $ 262-262
q23 $ 263-263
q24 $ 264-264
q25 $ 265-265
q26 $ 266-266
q27 $ 267-267
q28 $ 268-268
q29 $ 269-269
q30 $ 270-270
q31 $ 271-271
q32 $ 272-272
q33 $ 273-273
q34 $ 274-274
q35 $ 275-275
q36 $ 276-276
q37 $ 277-277
q38 $ 278-278
q39 $ 279-279
q40 $ 280-280
q41 $ 281-281
q42 $ 282-282
q43 $ 283-283
q44 $ 284-284
q45 $ 285-285
q46 $ 286-286
q47 $ 287-287
q48 $ 288-288
q49 $ 289-289
q50 $ 290-290
q51 $ 291-291
q52 $ 292-292
q53 $ 293-293
q54 $ 294-294
q55 $ 295-295
q56 $ 296-296
q57 $ 297-297
q58 $ 298-298
q59 $ 299-299
q60 $ 300-300
q64 $ 301-301
q65 $ 302-302
q66 $ 303-303
q67 $ 304-304
q68 $ 305-305
q69 $ 306-306
q70 $ 307-307
q71 $ 308-308
q72 $ 309-309
q73 $ 310-310
q74 $ 311-311
q75 $ 312-312
q76 $ 313-313
q77 $ 314-314
q78 $ 315-315
q79 $ 316-316
q80 $ 317-317
q81 $ 318-318
q82 $ 319-319
q83 $ 320-320
q84 $ 321-321
q85 $ 322-322
q86 $ 323-323
qn7 324-326
qn8 327-329
qn9 330-332
qn10 333-335
qn11 336-338
qn12 339-341
qn13 342-344
qn14 345-347
qn15 348-350
qn16 351-353
qn17 354-356
qn18 357-359
qn19 360-362
qn20 363-365
qn21 366-368
qn22 369-371
qn23 372-374
qn24 375-377
qn25 378-380
qn26 381-383
qn27 384-386
qn28 387-389
qn29 390-392
qn30 393-395
qn31 396-398
qn32 399-401
qn33 402-404
qn34 405-407
qn35 408-410
qn36 411-413
qn37 414-416
qn38 417-419
qn39 420-422
qn40 423-425
qn41 426-428
qn42 429-431
qn43 432-434
qn44 435-437
qn45 438-440
qn46 441-443
qn47 444-446
qn48 447-449
qn49 450-452
qn50 453-455
qn51 456-458
qn52 459-461
qn53 462-464
qn54 465-467
qn55 468-470
qn56 471-473
qn57 474-476
qn58 477-479
qn59 480-482
qn60 483-485
qn64 486-488
qn65 489-491
qn66 492-494
qn67 495-497
qn68 498-500
qn69 501-503
qn70 504-506
qn71 507-509
qn72 510-512
qn73 513-515
qn74 516-518
qn75 519-521
qn76 522-524
qn77 525-527
qn78 528-530
qn79 531-533
qn80 534-536
qn81 537-539
qn82 540-542
qn83 543-545
qn84 546-548
qn85 549-551
qn86 552-554
qnfrcig 555-557
qndaycig 558-560
qnfrevp 561-563
qndayevp 564-566
qnfrskl 567-569
qndayskl 570-572
qnfrcgr 573-575
qndaycgr 576-578
qntb2 579-581
qntb4 582-584
qnfrtb4 585-587
qndaytb4 588-590
qniudimp 591-593
qnothhpl 594-596
qnbcnone 597-599
qnconpp 600-602
qnfruit1 603-605
qnfruit2 606-608
qnfruit3 609-611
qnveg0 612-614
qnveg1 615-617
qnveg2 618-620
qnveg3 621-623
qnsoda1 624-626
qnsoda2 627-629
qnbk7day 630-632
qnpa0day 633-635
qnpa7day 636-638
qndlype 639-641
qnnodnt 642-644
qnfdinsc 645-647
qacessfirearm $ 648-648
qbasicneedsace $ 649-649
qbingeeating $ 650-650
qclimatechange $ 651-651
qclose2people $ 652-652
qconcentrating $ 653-653
qconsentsexcont $ 654-654
qcurrentopioid $ 655-655
qemoabuseace $ 656-656
qexpwttheraphy $ 657-657
qextremeheat $ 658-658
qhallucdrug $ 659-659
qincarparentace $ 660-660
qintviolenceace $ 661-661
qlivedwabuseace $ 662-662
qlivedwillace $ 663-663
qmusclestrength $ 664-664
qparentalmonitoring $ 665-665
qphyabuseace $ 666-666
qphyviolenceace $ 667-667
qsexabuseace $ 668-668
qspeakenglish $ 669-669
qsportsdrink $ 670-670
qsunburn $ 671-671
qtalkadultace $ 672-672
qtalkfriendace $ 673-673
qtimealonewthp $ 674-674
qunfairlyace $ 675-675
qunfairlydisc $ 676-676
qverbalabuseace $ 677-677
qwater $ 678-678
qnacessfirearm 679-681
qnbasicneedsace 682-684
qnbingeeating 685-687
qnclimatechange 688-690
qnclose2people 691-693
qnconcentrating 694-696
qnconsentsexcont 697-699
qncurrentopioid 700-702
qnemoabuseace 703-705
qnexpwttheraphy 706-708
qnextremeheat 709-711
qnhallucdrug 712-714
qnillict 715-717
qnincarparentace 718-720
qnintviolenceace 721-723
qnlivedwabuseace 724-726
qnlivedwillace 727-729
qnmusclestrength 730-732
qnparentalmonitoring 733-735
qnphyabuseace 736-738
qnphyviolenceace 739-741
qnsexabuseace 742-744
qnspeakenglish 745-747
qnsportsdrink 748-750
qnspdrk1 751-753
qnspdrk2 754-756
qnsunburn 757-759
qntalkadultace 760-762
qntalkfriendace 763-765
qntimealonewthp 766-768
qnunfairlyace 769-771
qnunfairlydisc 772-774
qnverbalabuseace 775-777
qnwater 778-780
qnwater1 781-783
qnwater2 784-786
qnwater3 787-789
;
 
/****************************************/
/*   Assign formats to SAS variables    */
/****************************************/
;
format
sitecode $SITE.
age AGE.
sex SEX.
grade GRADE.
race4 RACE.
race7 RACE7S.
q63 $H63S.
q62 $H62S.
q61 $H61S.
sexid SEXID.
sexid2 SEXIDB.
sexpart SEXPART.
sexpart2 SEXPARTB.
q7 $H7S.
q8 $H8S.
q9 $H9S.
q10 $H10S.
q11 $H11S.
q12 $H12S.
q13 $H13S.
q14 $H14S.
q15 $H15S.
q16 $H16S.
q17 $H17S.
q18 $H18S.
q19 $H19S.
q20 $H20S.
q21 $H21S.
q22 $H22S.
q23 $H23S.
q24 $H24S.
q25 $H25S.
q26 $H26S.
q27 $H27S.
q28 $H28S.
q29 $H29S.
q30 $H30S.
q31 $H31S.
q32 $H32S.
q33 $H33S.
q34 $H34S.
q35 $H35S.
q36 $H36S.
q37 $H37S.
q38 $H38S.
q39 $H39S.
q40 $H40S.
q41 $H41S.
q42 $H42S.
q43 $H43S.
q44 $H44S.
q45 $H45S.
q46 $H46S.
q47 $H47S.
q48 $H48S.
q49 $H49S.
q50 $H50S.
q51 $H51S.
q52 $H52S.
q53 $H53S.
q54 $H54S.
q55 $H55S.
q56 $H56S.
q57 $H57S.
q58 $H58S.
q59 $H59S.
q60 $H60S.
q64 $H64S.
q65 $H65S.
q66 $H66S.
q67 $H67S.
q68 $H68S.
q69 $H69S.
q70 $H70S.
q71 $H71S.
q72 $H72S.
q73 $H73S.
q74 $H74S.
q75 $H75S.
q76 $H76S.
q77 $H77S.
q78 $H78S.
q79 $H79S.
q80 $H80S.
q81 $H81S.
q82 $H82S.
q83 $H83S.
q84 $H84S.
q85 $H85S.
q86 $H86S.
qacessfirearm $FIRE.
qbasicneedsace $ACE2F.
qbingeeating $BEAT.
qclimatechange $CLCH.
qclose2people $CLPL.
qconcentrating $CONCEN.
qconsentsexcont $SEXCON.
qcurrentopioid $CURROPI.
qemoabuseace $ACE2F.
qexpwttheraphy $EWTH.
qextremeheat $EXHT.
qhallucdrug $LSD.
qincarparentace $ACE1F.
qintviolenceace $ACE2F.
qlivedwabuseace $ACE1F.
qlivedwillace $ACE1F.
qmusclestrength $MUSCLE.
qparentalmonitoring $ACE2F.
qphyabuseace $ACE2F.
qphyviolenceace $ACE3F.
qsexabuseace $ACE1F.
qspeakenglish $ENGLISH.
qsportsdrink $SPRTDRNK.
qsunburn $SUNBURN.
qtalkadultace $ACE2F.
qtalkfriendace $ACE2F.
qtimealonewthp $TAWD.
qunfairlyace $ACE2F.
qunfairlydisc $DISPLI.
qverbalabuseace $ACE3F.
qwater $WATER.
;
 
/****************************************/
/*   Assign labels to SAS variables    */
/****************************************/
;
label
sitecode="Site code"
sitename="Site name"
sitetype="Site type"
sitetypenum="1=District, 2=State, 3=National"
year="4-digit Year of survey"
survyear="1=1991...18=2025"
weight="Analysis weight"
stratum="Analysis stratum"
PSU="Analysis primary sampling unit"
record="Record ID"
age="1= <=12...7=18+ years old"
sex="1=female, 2=male"
grade="1=9th...4=12th grade"
race4="4-level race variable"
race7="7-level race variable"
stheight="Height in meters"
stweight="Weight in kilograms"
bmi="Body Mass Index"
bmipct="BMI percentile"
qnobese="Had obesity"
qnowt="Were overweight"
q63=""
q62=""
q61=""
sexid=""
sexid2=""
sexpart="Sex of sex contact(s)"
sexpart2="Collapsed sex of sex contact(s)"
q7="Seat belt use"
q8="Riding with a drinking driver"
q9="Drinking and driving"
q10="Texting and driving"
q11="Weapon carrying at school"
q12="Gun carrying"
q13="Safety concerns at school"
q14="Threatened at school"
q15="Physical fighting"
q16="Physical fighting at school"
q17="Saw physical violence in neighborhood"
q18="Forced sexual intercourse"
q19="Sexual violence"
q20="Sexual dating violence"
q21="Physical dating violence"
q22="Treated badly because of race or ethnicity"
q23="Bullying at school"
q24="Electronic bullying"
q25="Self harm >=1"
q26="Sad or hopeless"
q27="Considered suicide"
q28="Made a suicide plan"
q29="Attempted suicide"
q30="Injurious suicide attempt"
q31="Ever cigarette use"
q32="Initiation of cigarette smoking"
q33="Current cigarette use"
q34="Smoked > 10 cigarettes"
q35="Electronic vapor product use"
q36="Current electronic vapor use"
q37="EVP from store"
q38="Current smokeless tobacco use"
q39="Current cigar use"
q40="Initiation of alcohol use"
q41="Current alcohol use"
q42="Largest number of drinks"
q43="Source of alcohol"
q44="Ever marijuana use"
q45="Initiation of marijuana use"
q46="Current marijuana use"
q47="Ever prescription pain medicine use"
q48="Ever cocaine use"
q49="Ever inhalant use"
q50="Ever heroin use"
q51="Ever methamphetamine use"
q52="Ever ecstasy use"
q53="Illegal injected drug use"
q54="Ever sexual intercourse"
q55="Sex before 13 years"
q56="Number of sex partners"
q57="Current sexual activity"
q58="Alcohol/drugs and sex"
q59="Condom use"
q60="Birth control pill use"
q64="Perception of weight"
q65="Weight loss"
q66="Fruit eating"
q67="Green salad eating"
q68="Potato eating"
q69="Carrot eating"
q70="Other vegetable eating"
q71="No soda drinking"
q72="Breakfast eating"
q73="Physical activity >= 5 days"
q74="PE attendance"
q75="Sports team participation"
q76="Concussion"
q77="Social media"
q78="HIV testing"
q79="STD testing"
q80="Oral health care"
q81="Current mental health"
q82="Get help with emotions 12 mos"
q83="Sleep"
q84="Unstable housing"
q85="Worried food would run out"
q86="Food ran out"
qn7="Did not always wear a seat belt"
qn8="Rode with a driver who had been drinking alcohol"
qn9="Drove a car or other vehicle when they had been drinking alcohol"
qn10="Texted or e-mailed while driving a car or other vehicle"
qn11="Carried a weapon on school property"
qn12="Carried a gun"
qn13="Did not go to school because they felt unsafe at school or on their way to or from school"
qn14="Were threatened or injured with a weapon on school property"
qn15="Were in a physical fight"
qn16="Were in a physical fight on school property"
qn17="Ever saw someone get physically attacked, beaten, stabbed, or shot in their neighborhood"
qn18="Were ever physically forced to have sexual intercourse"
qn19="Experienced sexual violence"
qn20="Experienced sexual dating violence"
qn21="Experienced physical dating violence"
qn22="Felt that they were ever treated badly or unfairly in school because of their race or ethnicity"
qn23="Were bullied on school property"
qn24="Were electronically bullied"
qn25="Did something to purposely hurt themselves without wanting to die"
qn26="Felt sad or hopeless"
qn27="Seriously considered attempting suicide"
qn28="Made a plan about how they would attempt suicide"
qn29="Actually attempted suicide"
qn30="Had a suicide attempt that resulted in an injury, poisoning, or overdose that had to be treated by a doctor or nurse"
qn31="Ever smoked a cigarette"
qn32="Smoked a cigarette before age 13 years"
qn33="Currently smoked cigarettes"
qn34="Smoked more than 10 cigarettes per day"
qn35="Ever used an electronic vapor product"
qn36="Currently used an electronic vapor product"
qn37="Usually got their electronic vapor products by buying them themselves in a convenience store, supermarket, discount store, or gas station"
qn38="Currently used smokeless tobacco"
qn39="Currently smoked cigars"
qn40="Had their first drink of alcohol before age 13 years"
qn41="Currently drank alcohol"
qn42="Reported that the largest number of drinks they had in a row was 10 or more"
qn43="Usually got the alcohol they drank by someone giving it to them"
qn44="Ever used marijuana"
qn45="Tried marijuana for the first time before age 13 years"
qn46="Currently used marijuana"
qn47="Ever took prescription pain medicine without a doctor's prescription or differently than how a doctor told them to use it"
qn48="Ever used cocaine"
qn49="Ever used inhalants"
qn50="Ever used heroin"
qn51="Ever used methamphetamines"
qn52="Ever used ecstasy"
qn53="Ever injected any illegal drug"
qn54="Ever had sexual intercourse"
qn55="Had sexual intercourse for the first time before age 13 years"
qn56="Had sexual intercourse with four or more persons during their life"
qn57="Were currently sexually active"
qn58="Drank alcohol or used drugs before last sexual intercourse"
qn59="Used a condom during last sexual intercourse"
qn60="Used birth control pills before last sexual intercourse with opposite-sex partner"
qn64="Described themselves as slightly or very overweight"
qn65="Were trying to lose weight"
qn66="Did not eat fruit"
qn67="Did not eat salad"
qn68="Did not eat potatoes"
qn69="Did not eat carrots"
qn70="Did not eat other vegetables"
qn71="Did not drink a can, bottle, or glass of soda or pop"
qn72="Did not eat breakfast"
qn73="Were physically active at least 60 minutes per day on 5 or more days"
qn74="Attended physical education (PE) classes on 1 or more days"
qn75="Played on at least one sports team"
qn76="Had a concussion from playing a sport or being physically active"
qn77="Used social media several times"
qn78="Were ever tested for human immunodeficiency virus (HIV)"
qn79="Were tested for a sexually transmitted transmitted infection (STI) other than HIV, such as chlamydia or gonorrhea)"
qn80="Saw a dentist"
qn81="Reported that their mental health was most of the time or always not good"
qn82="Most of the time or always got the kind of help they needed when feeling sad, empty, hopeless, angry, or anxious"
qn83="Got 8 or more hours of sleep"
qn84="Experience unstable housing"
qn85="Reported their family sometimes, most of the time, or always worried that their food would run out before  they got money to buy more"
qn86="Reported sometimes, most of the time, or always the food their family bought ran out and they did not have money to buy more"
qnfrcig="Currently smoked cigarettes frequently"
qndaycig="Currently smoked cigarettes daily"
qnfrevp="Currently smoked electronic vapor products frequently"
qndayevp="Currently used electronic vapor products daily"
qnfrskl="Currently used smokeless tobacco frequently"
qndayskl="Currently used smokeless tobacco daily"
qnfrcgr="Currently smoked cigars frequently"
qndaycgr="Currently smoked cigars daily"
qntb2="Currently smoked cigarettes or cigars"
qntb4="Currently smoked cigarettes or cigars or used smokeless tobacco or electronic vapor products"
qnfrtb4="Currently smoked cigarettes or cigars or used smokeless tobacco or electronic vapor products frequently"
qndaytb4="Currently smoked cigarettes or cigars or used smokeless tobacco or electronic vapor products daily"
qniudimp="Used an IUD (such as Mirena or ParaGard) or implant (such as Implanon or Nexplanon) before last sexual intercourse with an opposite-sex partner"
qnothhpl="Used birth control pills; an IUD (such as Mirena or ParaGard) or implant (such as Implanon or Nexplanon); or a shot (such as Depo-Provera), patch (such as OrthoEvra), or birth control ring (such as NuvaRing) before last sexual intercourse with an opposite-"
qnbcnone="Did not use any method to prevent pregnancy during last sexual intercourse with an opposite-sex partner"
qnconpp="Used a condom as the primary method to prevent pregnancy before last sexual intercourse with an opposite-sex partner"
qnfruit1="Ate fruit one or more times per day"
qnfruit2="Ate fruit two or more times per day"
qnfruit3="Ate fruit three or more times per day"
qnveg0="Did not eat vegetables"
qnveg1="Ate vegetables one or more times per day"
qnveg2="Ate vegetables two or more times per day"
qnveg3="Ate vegetables three or more times per day"
qnsoda1="Drank a can, bottle, or glass of soda or pop one or more times per day"
qnsoda2="Drank a can, bottle, or glass of soda or pop two or more times per day"
qnbk7day="Ate breakfast on all 7 days"
qnpa0day="Did not participate in at least 60 minutes of physical activity on at least 1 day"
qnpa7day="Were physically active at least 60 minutes per day on all 7 days"
qndlype="Attended physical education (PE) classes on all 5 days"
qnnodnt="Never saw a dentist"
qnfdinsc="Food insecurity"
qacessfirearm="Loaded gun"
qbasicneedsace="Household adult tried hard to meet basic needs ACEs"
qbingeeating="Binge eating"
qclimatechange="Climate change"
qclose2people="Feel close to people at their school"
qconcentrating="Difficulty concentrating"
qconsentsexcont="Verbally asked for consent last sexual contact"
qcurrentopioid="Current Prescription pain medicine misuse"
qemoabuseace="Insulted at home"
qexpwttheraphy="Did not receive needed counseling or therapy"
qextremeheat="Extreme heat"
qhallucdrug="Ever used hallucinogenic drugs"
qincarparentace="Ever incarcerated parent/guardian ACEs"
qintviolenceace="Adults in home intimate partner violence ACEs"
qlivedwabuseace="Ever lived w/parent/guardian w/substance abuse ACEs"
qlivedwillace="Ever lived with parent/guardian w mental illness ACEs"
qmusclestrength="Muscle strengthening"
qparentalmonitoring="Parental monitoring"
qphyabuseace="Physically abused at home"
qphyviolenceace="Past 12-month incidence of physical violence"
qsexabuseace="Ever sexual abuse by adult or older person ACEs"
qspeakenglish="How well speak English"
qsportsdrink="Sports drinks"
qsunburn="Sunburn"
qtalkadultace="Lifetime prevalence of feeling able to talk to adults about feelings"
qtalkfriendace="Lifetime prevalence of feeling supported by friends"
qtimealonewthp="Time alone with doctor or nurse"
qunfairlyace="Lifetime prevalence of perceived racial/ethnic injustice"
qunfairlydisc="Unfairly disciplined at school"
qverbalabuseace="Past 12-month incidence of emotional violence"
qwater="Plain water"
qnacessfirearm="Could obtain a loaded gun ready for them to fire without a parent or other adult's permission or supervision"
qnbasicneedsace="Reported that an adult in their household most of the time or always tried to make sure their basic needs were met"
qnbingeeating="Ate an unusually large amount of food in a short period of time and experienced a loss of control over how much they were eating or a feeling that they could not stop eating even when full"
qnclimatechange="Reported being worried or very worried about climate change"
qnclose2people="Strongly agree or agree that they feel close to people at their school"
qnconcentrating="Have serious difficulty concentrating, remembering, or making decisions"
qnconsentsexcont="Verbally asked for consent the last time they had sexual contact"
qncurrentopioid="Currently took prescription pain medicine without a doctor's prescription or differently than how a doctor told them to use it"
qnemoabuseace="Were insulted at home"
qnexpwttheraphy="needed counseling or therapy but did not get it because of cost, not knowing how or where to get help, or another reason"
qnextremeheat="Reported being worried or very worried about extreme heat"
qnhallucdrug="Ever used hallucinogenic drugs"
qnillict="Ever used select illicit drugs"
qnincarparentace="Have ever been separated from a parent or guardian because they went to jail, prison, or a detention center"
qnintviolenceace="Reported that their parents or other adults in their home most of the time or always slapped, hit, kicked, punched, or beat each other up"
qnlivedwabuseace="Ever lived with a parent or guardian who was having a problem with alcohol or drug use"
qnlivedwillace="Ever lived with a parent or guardian who had severe depression, anxiety, or another mental illness, or was suicidal"
qnmusclestrength="Did exercises to strengthen or tone their muscles on three or more days"
qnparentalmonitoring="Reported that their parents or other adults in their family most of the time or always know where they are going or with whom they will be"
qnphyabuseace="Were physically abused at home"
qnphyviolenceace="Reported that a parent or other adult in their home hit, beat, kicked, or physically hurt them in any way one or more times"
qnsexabuseace="Reported that an adult or person at least 5 years older than them ever made them do sexual things they did not want to do"
qnspeakenglish="Speak English well or very well"
qnsportsdrink="Did not drink a can, bottle, or glass of a sports drink"
qnspdrk1="Drank a can, bottle, or glass of a sports drink one or more times per day"
qnspdrk2="Drank a can, bottle, or glass of a sports drink two or more times per day"
qnsunburn="Had a sunburn"
qntalkadultace="Most of the time or always feel that they are able to talk to an adult in their family or another caring adult about their feelings"
qntalkfriendace="Most of the time or always feel that they are able to talk to a friend about their feelings"
qntimealonewthp="Talked with the doctor or nurse about their health and behaviors without a parent or guardian being in the room with them"
qnunfairlyace="Felt that they were treated badly or unfairly because of their race or ethnicity"
qnunfairlydisc="Have been unfairly disciplined at school"
qnverbalabuseace="Reported that a parent or other adult in their home hit, beat, kicked, or physically hurt them in any way one or more times"
qnwater="Did not drink a bottle or glass of plain water"
qnwater1="Drank a bottle or glass of plain water one or more times per day"
qnwater2="Drank a bottle or glass of plain water two or more times per day"
qnwater3="Drank a bottle or glass of plain water three or more times per day"
;
run;

