#####################################################
# Chicago's NAEP Story — Explorer
# Companion dashboard to the Chicago NAEP brief
# Tabs: Key Takeaways | Chicago Over Time | Who's Left Behind | Peer Comparison
# Data: NAEP_Compiled_Wide.xlsx (same folder as app.R)
#####################################################

library(shiny)
library(bslib)
library(dplyr)
library(tidyr)
library(tidyverse)
library(plotly)
library(readxl)

K1C_GREEN      <- "#2C8C4C"
K1C_DARK_GREEN <- "#1B4D25"
K1C_LIGHT      <- "#E8F5EE"
ORANGE         <- "#C05621"
GRAY           <- "#718096"
GRAY_LIGHT     <- "#E2E8F0"
GRAY_BG        <- "#F7F9F7"
IL_COLOR       <- "#2B6CB0"
NAT_COLOR      <- "#718096"
CHI_COLOR      <- K1C_GREEN
PEER_COLS <- c("#C05621","#6B46C1","#B7791F","#2C7A7B","#97266D","#744210","#2B6CB0","#276749")

APP_TITLE    <- "Chicago's NAEP Story"
APP_SUBTITLE <- "Explore how Chicago and other large districts perform on the National Assessment of Educational Progress (NAEP) — also known as the Nation's Report Card — over time and in comparison."
FAVICON <- "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='46' fill='%231B4D25'/%3E%3Ctext x='50' y='68' font-size='54' text-anchor='middle' fill='white' font-family='Arial,sans-serif' font-weight='700'%3EN%3C/text%3E%3C/svg%3E"

reforms <- list(
  list(year=2015,label="ESSA",level="federal",scope="both",
  list(year=2020,label="COVID closures",level="federal",scope="both",
       desc="COVID-19. Illinois schools closed March 2020; most CPS students remained remote through SY2020-21."),
  list(year=2021,label="CPS Skyline",level="chicago",scope="both",
       desc="CPS launched Skyline, universal PreK-12 curriculum (SY2021-22). First district-wide curriculum in ELA and math."),
  list(year=2022,label="CPS literacy shift",level="chicago",scope="reading",
       desc="CPS announced shift toward structured literacy / science of reading (Aug 2022). No mandated programs; schools retained curriculum autonomy."),
  list(year=2023,label="IL SB 2243",level="illinois",scope="reading",
       desc="Illinois SB 2243 (Literacy and Justice for All Act) passed May 2023. Required ISBE to create a literacy plan by Jan 2024 and a curriculum rubric by July 2024."),
  list(year=2024,label="IL Literacy Plan",level="illinois",scope="reading",
       desc="Illinois Comprehensive Literacy Plan finalized by ISBE (Jan 2024). Non-mandatory guidance for evidence-based reading instruction statewide.")
)
reform_colors <- c(federal="black",illinois=IL_COLOR,chicago=CHI_COLOR)

naep_wide <- read_excel("NAEP_Compiled_Wide.xlsx",sheet="Sheet1")
naep_wide <- naep_wide %>% filter(Year >= 2003)

naep <- naep_wide |>
  rename(year=Year,jurisdiction=Jurisdiction,subject=Subject,grade=Grade) |>
  mutate(grade=as.integer(grade),subject=str_trim(subject)) |>
  pivot_longer(`All students`:`Not identified as students with disabilities`,
               names_to="cat_value",values_to="score") |>
  filter(!is.na(score)) |>
  mutate(
    score=as.numeric(score),
    cat_label=case_when(
      cat_value=="All students" ~ "All students",
      cat_value %in% c("White","Black","Hispanic","Asian/Pacific Islander",
                       "American Indian/Alaska Native","Two or more races") ~ "Race/Ethnicity",
      cat_value %in% c("Male","Female") ~ "Sex",
      cat_value %in% c("Economically disadvantaged","Not economically disadvantaged",
                       "Information not available") ~ "Econ. Disadvantage",
      cat_value %in% c("ELL","Not ELL") ~ "English Learner",
      cat_value %in% c("Identified as students with disabilities",
                       "Not identified as students with disabilities") ~ "Disability Status",
      TRUE ~ NA_character_)) |>
  filter(!is.na(cat_label))

NON_DISTRICTS <- c("National","National public","Large city","Illinois")
TUDA <- naep |> filter(!jurisdiction %in% NON_DISTRICTS) |> pull(jurisdiction) |> unique() |> sort()
SIMILAR_PEERS   <- c("Houston","Fort Worth (TX)","Los Angeles","Boston","Dallas","New York City")
HIGH_PERFORMERS <- c("San Diego","Charlotte","Austin","Miami-Dade","Hillsborough County (FL)")
PEER_GROUPS <- list(
  "Demographically similar"=SIMILAR_PEERS,
  "High performers"=HIGH_PERFORMERS,
  "All TUDA"=TUDA)
ALL_JUR_CHOICES <- c("Chicago",sort(TUDA[TUDA!="Chicago"]),"National public","Illinois","Large city")

`%||%` <- function(a,b) if(!is.null(a)&&length(a)>0) a else b

get_score <- function(jur,subj,gr,yr,catv="All students") {
  v <- naep |> filter(jurisdiction==jur,subject==subj,grade==as.integer(gr),year==as.integer(yr),cat_value==catv) |> pull(score)
  if(length(v)==0) NA_real_ else v[1]
}
fnum <- function(x,digits=0) if(is.na(x)) "—" else format(round(x,digits),nsmall=digits)
fsigned <- function(x,digits=0) if(is.na(x)) "—" else if(x>0) paste0("+",format(round(x,digits),nsmall=digits)) else format(round(x,digits),nsmall=digits)
gaincol <- function(x) if(is.na(x)) GRAY else if(x>0) "#276749" else "#c53030"

sec_lbl <- function(txt) tags$div(
  style="font-size:11px;font-weight:700;color:#4a5568;letter-spacing:1px;text-transform:uppercase;margin-top:14px;margin-bottom:5px;",txt)

ibox <- function(...) tags$div(
  style="background:white;border:1px solid #e2e8f0;border-radius:4px;padding:12px 16px;margin-bottom:14px;font-size:13px;line-height:1.7;color:#4a5568;",...)


notebox <- function(...) tags$div(
  style=paste0("background:#FFFAF0;border-left:4px solid ",ORANGE,
               ";border-radius:4px;padding:12px 16px;margin-bottom:14px;font-size:12.5px;line-height:1.65;color:#4a5568;"),...)

kbox <- function(val,lbl,col=K1C_GREEN) tags$div(
  style=paste0("background:white;border:1px solid #e2e8f0;border-top:3px solid ",col,
               ";border-radius:4px;padding:12px 14px;text-align:center;flex:1;"),
  tags$div(style=paste0("font-size:24px;font-weight:700;color:",col,";line-height:1.1;"),val),
  tags$div(style="font-size:11px;color:#718096;margin-top:3px;",lbl))

cpanel <- function(...,title=NULL) tags$div(class="card-panel",
                                            if(!is.null(title)) tags$div(class="card-title",title),...)

helptip <- function(text) tags$span(title=text,style="cursor:help;color:#a0aec0;font-weight:700;font-size:11px;margin-left:5px;border:1px solid #cbd5e0;border-radius:50%;padding:0px 5px;","i")

kt_card <- function(n,headline,body,stat_ui=NULL,btn_id=NULL,btn_label="See the evidence") tags$div(
  style="background:white;border:1px solid #e2e8f0;border-radius:6px;padding:16px 18px;margin-bottom:12px;display:flex;gap:14px;align-items:flex-start;",
  tags$div(style=paste0("flex:0 0 30px;height:30px;width:30px;border-radius:50%;background:",K1C_GREEN,
                        ";color:white;font-weight:700;font-size:14px;display:flex;align-items:center;justify-content:center;"),n),
  tags$div(style="flex:1;",
           tags$div(style="font-size:14px;font-weight:700;color:#1a202c;margin-bottom:4px;",headline),
           tags$div(style="font-size:12.5px;color:#4a5568;line-height:1.6;margin-bottom:8px;",body),
           if(!is.null(stat_ui)) stat_ui,
           if(!is.null(btn_id)) actionLink(btn_id,paste0(btn_label," →"),
                                           style=paste0("font-size:12px;font-weight:600;color:",K1C_GREEN,";"))
  )
)

quick_chip <- function(id,label) actionButton(id,label,class="quick-chip")

ui <- fluidPage(
  title=paste0(APP_TITLE," | Explorer"),
  theme=bs_theme(version=5,bootswatch="lumen"),
  tags$head(
    tags$link(rel="icon",type="image/svg+xml",href=FAVICON),
    tags$link(href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap",rel="stylesheet"),
    tags$style(HTML(paste0("
      *{font-family:'Montserrat',sans-serif;}
      body{background:",GRAY_BG,";}
      .title-header{background:",K1C_DARK_GREEN,";color:white;padding:16px 24px;margin-bottom:20px;border-radius:4px;
                    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
      .title-header h2{margin:0;font-size:18px;font-weight:700;}
      .title-header p{margin:2px 0 0 0;font-size:12px;opacity:.8;}
      .header-btns{display:flex;gap:8px;align-items:center;}
      .btn-howto{background:rgba(255,255,255,.12);color:white;border:1px solid rgba(255,255,255,.4);
                 font-size:12px;font-weight:600;border-radius:4px;padding:6px 12px;}
      .btn-howto:hover{background:rgba(255,255,255,.22);color:white;}
      .data-badge{font-size:10px;background:rgba(255,255,255,.15);padding:3px 8px;border-radius:10px;}
      .sidebar-panel{background:white;border:1px solid #e2e8f0;border-radius:4px;padding:16px 14px;}
      .card-panel{background:white;border:1px solid #e2e8f0;border-radius:4px;padding:16px;margin-bottom:14px;}
      .card-title{font-size:13px;font-weight:600;color:#2d3748;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e2e8f0;}
      .kpi-row{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;}
      .nav-tabs .nav-link.active{background-color:",K1C_GREEN,"!important;color:white!important;border-color:",K1C_GREEN,"!important;font-weight:600;}
      .nav-tabs .nav-link{color:",K1C_DARK_GREEN,";font-size:13px;font-weight:600;}
      label{font-size:12px;color:#4a5568;font-weight:600;}
      hr{border-color:#e2e8f0;margin:10px 0;}
      .reform-chip{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;margin:2px;}
      .chip-federal{background:#2d3748;color:white;}
      .chip-illinois{background:",IL_COLOR,";color:white;}
      .chip-chicago{background:",K1C_GREEN,";color:white;}
      .quick-chip{background:",K1C_LIGHT,";color:",K1C_DARK_GREEN,";border:1px solid #bbe3cc;border-radius:14px;
                  font-size:11.5px;font-weight:600;padding:5px 12px;margin:0 6px 8px 0;}
      .quick-chip:hover{background:",K1C_GREEN,";color:white;}
      .reset-link{font-size:11px;color:#a0aec0;font-weight:600;}
      .reset-link:hover{color:",ORANGE,";}
      .app-footer{font-size:11px;color:#a0aec0;text-align:center;padding:22px 10px 30px 10px;line-height:1.7;}
      .app-footer b{color:#718096;}
    ")))
  ),
  div(class="title-header",
      div(style="display:flex;align-items:center;gap:12px;",
          tags$img(src="K1C_Logo_FINAL1.png",style="height:44px;width:auto;display:block;"),
          div(tags$h2(APP_TITLE),
              tags$p(APP_SUBTITLE))),
      div(class="header-btns",
          tags$span(class="data-badge","Data through 2024"),
          actionButton("btn_howto","How to Read NAEP ▸",class="btn-howto"))),
  
  tabsetPanel(id="main_tabs",
              
              
              tabPanel("Chicago Over Time",value="summary",br(),
                       fluidRow(
                         column(3,div(class="sidebar-panel",
                                      sec_lbl("District"),
                                      selectInput("d_summary",NULL,choices=ALL_JUR_CHOICES,selected="Chicago"),
                                      hr(),
                                      sec_lbl("Grade"),
                                      radioButtons("s_grade",NULL,choices=c("Grade 4"=4,"Grade 8"=8),selected=4,inline=TRUE),
                                      hr(),
                                      sec_lbl("Policy Overlays"),
                                      tags$p(style="font-size:11px;color:#718096;margin-bottom:6px;",
                                             "Shown for reference only — these mark when key reforms took place. They do not imply the reform caused any change in scores."),
                                      checkboxGroupInput("s_ov_fed","Federal:",
                                                         choices=c("ESSA (2015)"="ESSA","COVID (2020)"="COVID closures"),
                                                         selected="COVID closures"),
                                      checkboxGroupInput("s_ov_il","Illinois:",
                                                         choices=c("SB 2243 — Literacy law (2023)"="IL SB 2243",
                                                                   "IL Literacy Plan finalized (2024)"="IL Literacy Plan"),
                                                         selected=character(0)),
                                      checkboxGroupInput("s_ov_cps","Chicago:",
                                                         choices=c("Skyline curriculum (2021)"="CPS Skyline",
                                                                   "Structured literacy shift (2022)"="CPS literacy shift"),
                                                         selected=character(0)),
                                      hr(),
                                      sec_lbl("About Selected Overlays"),
                                      uiOutput("s_reform_details"),
                                      hr(),
                                      actionLink("s_reset","↺ Reset this tab",class="reset-link")
                         )),
                         column(9,
                                uiOutput("s_ibox"),
                                cpanel(title="2024 Snapshot: Average Scale Scores",uiOutput("s_kpi_row")),
                                cpanel(title=uiOutput("s_read_title"),plotlyOutput("s_read_chart",height="280px")),
                                cpanel(title=uiOutput("s_math_title"),plotlyOutput("s_math_chart",height="280px"))
                         )
                       )
              ),
              
              tabPanel("Who's Left Behind",value="trend",br(),
                       fluidRow(
                         column(3,div(class="sidebar-panel",
                                      sec_lbl("District"),
                                      selectInput("d_trend",NULL,choices=ALL_JUR_CHOICES,selected="Chicago"),
                                      hr(),
                                      sec_lbl("Subject & Grade"),
                                      selectInput("t_subject",NULL,choices=c("Mathematics","Reading"),selected="Mathematics"),
                                      radioButtons("t_grade",NULL,choices=c("Grade 4"=4,"Grade 8"=8),selected=4,inline=TRUE),
                                      hr(),
                                      sec_lbl("Subgroup"),
                                      selectInput("t_category",NULL,
                                                  choices=c("All students"="All students","Race"="Race/Ethnicity",
                                                            "Economically Disadvantaged"="Econ. Disadvantage","Gender"="Sex",
                                                            "English Learner"="English Learner","Disability Status"="Disability Status"),
                                                  selected="Race/Ethnicity"),
                                      hr(),
                                      actionLink("t_reset","↺ Reset this tab",class="reset-link")
                         )),
                         column(9,
                                tags$div(style="margin-bottom:10px;",
                                         tags$span(style="font-size:11px;color:#718096;font-weight:600;margin-right:6px;","Jump to a gap from the brief:"),
                                         quick_chip("wlb_race","Racial gaps in math"),
                                         quick_chip("wlb_econ","Economic gaps in math"),
                                         quick_chip("wlb_gender","Gender gaps in reading")),
                                uiOutput("t_info_box"),
                                cpanel(uiOutput("t_kpi_row")),
                                uiOutput("t_main_panel"),
                                cpanel(title=uiOutput("t_chart_title_ui"),
                                       tags$div(style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px;",
                                                tags$div(style="min-width:170px;",tags$div(style="font-size:11px;color:#718096;font-weight:600;margin-bottom:3px;","Subgroup"),
                                                         uiOutput("t_subgroup_ui")),
                                                tags$div(style="min-width:170px;",tags$div(style="font-size:11px;color:#718096;font-weight:600;margin-bottom:3px;","Compare to"),
                                                         tags$div(style="display:flex;gap:10px;align-items:center;padding-top:6px;",
                                                                  checkboxInput("t_national","National public",value=TRUE),
                                                                  checkboxInput("t_illinois","Illinois",value=TRUE),
                                                                  checkboxInput("t_largecity","Large city",value=FALSE)))),
                                       plotlyOutput("t_trend_chart",height="420px"))
                         )
                       )
              ),
              
              tabPanel("Peer Comparison",value="peer",br(),
                       fluidRow(
                         column(3,div(class="sidebar-panel",
                                      sec_lbl("District"),
                                      selectInput("d_peer",NULL,choices=ALL_JUR_CHOICES,selected="Chicago"),
                                      hr(),
                                      sec_lbl("Subject & Grade"),
                                      selectInput("p_subject",NULL,choices=c("Mathematics","Reading"),selected="Mathematics"),
                                      radioButtons("p_grade",NULL,choices=c("Grade 4"=4,"Grade 8"=8),selected=4,inline=TRUE),
                                      hr(),
                                      sec_lbl("Year"),
                                      uiOutput("p_year_ui"),
                                      hr(),
                                      sec_lbl("Display"),
                                      radioButtons("p_sort","Sort:",
                                                   choices=c("Score (high to low)"="desc","Score (low to high)"="asc","Alphabetical"="alpha"),
                                                   selected="desc"),
                                      checkboxInput("p_natline","National avg line",value=TRUE),
                                      checkboxInput("p_highlight","Highlight similar districts",value=TRUE),
                                      hr(),
                                      sec_lbl("Filter Districts"),
                                      checkboxGroupInput("p_filter",NULL,
                                                         choices=c("All TUDA districts"="all","Demographically similar"="similar","High performers"="high"),
                                                         selected="all"),
                                      hr(),
                                      actionLink("p_reset","↺ Reset this tab",class="reset-link")
                         )),
                         column(9,
                                uiOutput("p_why_box"),
                                uiOutput("p_info_box"),
                                cpanel(title=uiOutput("p_snapshot_title"),plotlyOutput("p_dot_chart",height="500px"),uiOutput("p_legend_ui")),
                                cpanel(title=uiOutput("p_rank_title"),plotlyOutput("p_rank_chart",height="200px")),
                                notebox(tags$b("A note on rankings and margins of error: "),
                                        "this dashboard ranks districts by their point estimate of the average scale score. It does not run a statistical significance test between districts — two districts shown a few points apart may not be meaningfully different once sampling error is taken into account. For confirmed significant differences, consult NAEP's own significance testing in the ",tags$a(href="https://www.nationsreportcard.gov/ndecore/xplore/NDE",target="_blank","NAEP Data Explorer"),".")
                         )
                       )
              )
  ),
  tags$div(class="app-footer",
           tags$b("Source: "),"NAEP Trends in Urban Districts Assessment (TUDA), National Center for Education Statistics, 2003–2024.",tags$br(),
           "Built as a companion to “Chicago's NAEP Story.” Figures are point estimates; see each tab for margin-of-error notes.")
)

server <- function(input,output,session) {
  
  district_rv <- reactiveVal("Chicago")
  sel_district <- reactive({ district_rv() })
  observeEvent(input$d_summary,{ if(!is.null(input$d_summary) && input$d_summary!=district_rv()) district_rv(input$d_summary) })
  observeEvent(input$d_trend,  { if(!is.null(input$d_trend)   && input$d_trend  !=district_rv()) district_rv(input$d_trend) })
  observeEvent(input$d_peer,   { if(!is.null(input$d_peer)    && input$d_peer   !=district_rv()) district_rv(input$d_peer) })
  observeEvent(district_rv(),{
    updateSelectInput(session,"d_summary",selected=district_rv())
    updateSelectInput(session,"d_trend",selected=district_rv())
    updateSelectInput(session,"d_peer",selected=district_rv())
  },ignoreInit=TRUE)
  
  get_overlays <- function(sel,scope="both") {
    if(length(sel)==0) return(list(shapes=list(),annotations=list()))
    rel <- Filter(function(r) r$label %in% sel && r$label!="COVID closures" &&
                    (r$scope=="both"||scope=="both"||r$scope==scope), reforms)
    sh <- an <- list()
    for(r in rel) {
      col <- reform_colors[[r$level]]
      sh <- c(sh,list(list(type="line",xref="x",yref="paper",x0=r$year,x1=r$year,y0=0,y1=1,
                           line=list(color=col,dash="dot",width=1.5))))
      an <- c(an,list(list(xref="x",yref="paper",x=r$year,y=1.05,text=r$label,
                           showarrow=FALSE,textangle=-30,font=list(color=col,size=9),xanchor="left")))
    }
    # COVID is shown as the original shaded range (2019-2022) rather than a dotted line
    if("COVID closures" %in% sel) {
      sh <- c(sh,list(list(type="rect",xref="x",yref="paper",x0=2019,x1=2022,y0=0,y1=1,
                           fillcolor="#f6ad55",opacity=0.15,line=list(width=0))))
      an <- c(an,list(list(xref="x",yref="paper",x=2020.5,y=1.05,text="COVID",
                           showarrow=FALSE,font=list(color=ORANGE,size=9))))
    }
    list(shapes=sh,annotations=an)
  }
  
  add_line <- function(p,df,name,color,lwd=2,sz=6,dash="solid",open=FALSE) {
    sym <- if(open) "circle-open" else "circle"
    p |> add_trace(data=df|>arrange(year),x=~year,y=~score,type="scatter",mode="lines+markers",name=name,
                   line=list(color=color,width=lwd,dash=dash),
                   marker=list(color=color,size=sz,symbol=sym,
                               line=list(color=if(!open)"white" else color,width=if(!open)1.5 else 1.5)),
                   hovertemplate=paste0("<b>",name,"</b><br>%{x}: %{y:.0f}<extra></extra>"))
  }
  
  base_layout <- function(p,sh=list(),an=list()) {
    p |> layout(
      xaxis=list(title="Year",tickformat="d",showgrid=FALSE,dtick=2),
      yaxis=list(title="Average Scale Score",showgrid=TRUE,gridcolor=GRAY_LIGHT,zeroline=FALSE),
      legend=list(orientation="h",y=-0.22,x=0,font=list(size=11)),
      hovermode="x unified",plot_bgcolor="white",paper_bgcolor="white",
      margin=list(l=60,r=20,t=50,b=80),shapes=sh,annotations=an
    ) |> config(displayModeBar=FALSE)
  }
  
  empty_chart <- function(msg="No data available for this selection. NCES suppresses estimates for very small student groups.") {
    plot_ly() |> layout(
      xaxis=list(visible=FALSE),yaxis=list(visible=FALSE),
      plot_bgcolor="white",paper_bgcolor="white",
      annotations=list(list(text=msg,xref="paper",yref="paper",x=0.5,y=0.5,showarrow=FALSE,
                            font=list(size=12,color=GRAY),align="center"))
    ) |> config(displayModeBar=FALSE)
  }
  
  # HOW TO READ NAEP (modal)
  observeEvent(input$btn_howto,{
    showModal(modalDialog(
      title="How to Read NAEP",easyClose=TRUE,size="l",
      tags$div(style="font-size:13px;line-height:1.75;color:#2d3748;",
               tags$p(tags$b("Scale scores. "),"NAEP reports an average ",tags$b("scale score"),
                      " for each subject and grade (0–500 for math, 0–500 for reading at grade 4/8). It is not a percentage correct — it's a position on a fixed scale that lets you compare years, districts, and student groups consistently over time."),
               tags$p(tags$b("TUDA. "),"The ",tags$b("Trends in Urban Districts Assessment"),
                      " , formerly known as Trial Urban District Assessment, is the subset of NAEP that reports results for individual large urban districts — including Chicago — rather than only states and the nation. It's what makes district-to-district comparison possible."),
               tags$p(tags$b("National Public vs. National. "),
                      "“National public” includes only public-school students, which is the fairest comparison for a public district like Chicago."),
               tags$p(tags$b("Gaps. "),"A “gap” on this dashboard is the difference in average scale score between a reference group (e.g. White students, or students not economically disadvantaged) and the subgroup being examined. A widening gap means the two groups are drifting further apart, even if both groups' scores are rising."),
               tags$p(tags$b("Margins of error. "),"Every score shown is estimated from a sample, not a full census of students. Small year-to-year moves or close rankings between districts may fall within the margin of error — treat them as noisy rather than definitive. See the caveats on the Peer Comparison tab."),
               tags$p(tags$b("Suppressed data. "),"Some student groups in some districts/years are too small to report reliably and are omitted by NCES; you may see a subgroup or district disappear from a chart in certain years for this reason.")
      )
    ))
  })
  
  # OVERVIEW / KEY TAKEAWAYS
  output$ov_kpi_grid <- renderUI({
    d <- sel_district()
    g8r_c <- get_score(d,"Reading",8,2024); g8r_n <- get_score("National public","Reading",8,2024)
    g4m_c <- get_score(d,"Mathematics",4,2024); g4m_n <- get_score("National public","Mathematics",4,2024)
    g4r_c <- get_score(d,"Reading",4,2024); g4r_n <- get_score("National public","Reading",4,2024)
    g8m_c <- get_score(d,"Mathematics",8,2024); g8m_n <- get_score("National public","Mathematics",8,2024)
    div(class="kpi-row",style="flex-wrap:wrap;",
        kbox(fnum(g8r_c),"Gr 8 Reading",CHI_COLOR),
        kbox(fsigned(g8r_c-g8r_n),"vs National",gaincol(g8r_c-g8r_n)),
        kbox(fnum(g4m_c),"Gr 4 Math",CHI_COLOR),
        kbox(fsigned(g4m_c-g4m_n),"vs National",gaincol(g4m_c-g4m_n)),
        kbox(fnum(g4r_c),"Gr 4 Reading",CHI_COLOR),
        kbox(fsigned(g4r_c-g4r_n),"vs National",gaincol(g4r_c-g4r_n)),
        kbox(fnum(g8m_c),"Gr 8 Math",CHI_COLOR),
        kbox(fsigned(g8m_c-g8m_n),"vs National",gaincol(g8m_c-g8m_n))
    )
  })
  
  output$ov_kt1_stat <- renderUI({
    d <- sel_district()
    chi <- get_score(d,"Reading",8,2024); nat <- get_score("National public","Reading",8,2024)
    tags$div(style="font-size:12px;",tags$b(fnum(chi))," in 2024 — ",fsigned(chi-nat)," pts vs. national public")
  })
  output$ov_kt2_stat <- renderUI({
    d <- sel_district()
    m24 <- get_score(d,"Mathematics",4,2024); m19 <- get_score(d,"Mathematics",4,2019)
    r24 <- get_score(d,"Reading",4,2024); r03 <- get_score(d,"Reading",4,2003)
    tags$div(style="font-size:12px;","Gr4 math ",fsigned(m24-m19)," since 2019 · Gr4 reading ",fsigned(r24-r03)," since 2003")
  })
  output$ov_kt3_stat <- renderUI({
    d <- sel_district()
    y19 <- get_score(d,"Mathematics",4,2019); y22 <- get_score(d,"Mathematics",4,2022); y24 <- get_score(d,"Mathematics",4,2024)
    tags$div(style="font-size:12px;","Gr4 math: ",fnum(y19)," (2019) → ",fnum(y22)," (2022) → ",fnum(y24)," (2024)")
  })
  output$ov_kt4_stat <- renderUI({
    d <- sel_district()
    w24 <- get_score(d,"Mathematics",4,2024,"White"); b24 <- get_score(d,"Mathematics",4,2024,"Black")
    w03 <- get_score(d,"Mathematics",4,2003,"White"); b03 <- get_score(d,"Mathematics",4,2003,"Black")
    tags$div(style="font-size:12px;","Black–White Gr4 math gap: ",fnum(w03-b03)," pts (2003) → ",tags$b(fnum(w24-b24))," pts (2024)")
  })
  output$ov_kt5_stat <- renderUI({
    tags$div(style="font-size:12px;",length(SIMILAR_PEERS)," peer districts tracked: ",paste(SIMILAR_PEERS,collapse=", "))
  })
  
  output$ov_covid_chart <- renderPlotly({
    df <- naep |> filter(jurisdiction==sel_district(),subject=="Mathematics",grade==4,cat_value=="All students")
    if(nrow(df)==0) return(empty_chart())
    plot_ly(df|>arrange(year),x=~year,y=~score,type="scatter",mode="lines+markers",
            line=list(color=CHI_COLOR,width=2.5),marker=list(color=CHI_COLOR,size=7),
            hovertemplate="%{x}: %{y:.0f}<extra></extra>")|>
      layout(shapes=list(list(type="rect",xref="x",yref="paper",x0=2019,x1=2022,y0=0,y1=1,fillcolor="#f6ad55",opacity=0.15,line=list(width=0))),
             annotations=list(list(xref="x",yref="paper",x=2020.5,y=0.95,text="COVID",showarrow=FALSE,font=list(color=ORANGE,size=10))),
             xaxis=list(title="",tickformat="d",showgrid=FALSE,dtick=4),
             yaxis=list(title="Scale score",showgrid=TRUE,gridcolor=GRAY_LIGHT),
             plot_bgcolor="white",paper_bgcolor="white",margin=list(l=45,r=15,t=15,b=30))|>config(displayModeBar=FALSE)
  })
  
  jump_to <- function(tab) updateTabsetPanel(session,"main_tabs",selected=tab)
  
  observeEvent(input$ov_jump1,{
    updateRadioButtons(session,"s_grade",selected=8); jump_to("summary")
  })
  observeEvent(input$ov_jump2,{
    updateRadioButtons(session,"s_grade",selected=4); jump_to("summary")
  })
  observeEvent(input$ov_jump3,{
    updateSelectInput(session,"t_subject",selected="Mathematics")
    updateRadioButtons(session,"t_grade",selected=4)
    updateSelectInput(session,"t_category",selected="All students")
    jump_to("trend")
  })
  observeEvent(input$ov_jump4,{
    updateSelectInput(session,"t_subject",selected="Mathematics")
    updateRadioButtons(session,"t_grade",selected=4)
    updateSelectInput(session,"t_category",selected="Race/Ethnicity")
    jump_to("trend")
  })
  observeEvent(input$ov_jump5,{
    updateSelectInput(session,"p_subject",selected="Mathematics")
    updateRadioButtons(session,"p_grade",selected=4)
    updateCheckboxGroupInput(session,"p_filter",selected="similar")
    jump_to("peer")
  })
  
  # SUMMARY / DISTRICT OVER TIME
  output$s_grade_inline <- renderUI({ input$s_grade })
  output$s_ibox <- renderUI({
    d <- sel_district()
    ibox(tags$b(paste0("Comparison of Average Scale Scores National Public → Illinois → ",d)),tags$br(),
         "Average scale scores for all students, Grade ",input$s_grade," reading and math, 2003–2024.")
  })
  output$s_read_title   <- renderUI({ paste0("Reading · Grade ",input$s_grade," — National Public, Illinois, ",sel_district()) })
  output$s_math_title   <- renderUI({ paste0("Mathematics · Grade ",input$s_grade," — National Public, Illinois, ",sel_district()) })
  
  s_ov <- reactive({ c(input$s_ov_fed%||%character(0),input$s_ov_il%||%character(0),input$s_ov_cps%||%character(0)) })
  
  make_sum_chart <- function(subj) {
    d <- sel_district()
    df <- naep |> filter(subject==subj,grade==as.integer(input$s_grade),cat_value=="All students",
                         jurisdiction %in% unique(c("National public","Illinois",d)))
    if(nrow(df)==0) return(empty_chart())
    ov <- get_overlays(s_ov(),tolower(subj))
    p <- plot_ly()
    nat <- df|>filter(jurisdiction=="National public")
    il  <- df|>filter(jurisdiction=="Illinois")
    foc <- df|>filter(jurisdiction==d)
    if(nrow(nat)>0) p <- add_line(p,nat,"National Public",NAT_COLOR,lwd=1.5,sz=5,dash="dash",open=TRUE)
    if(nrow(il)>0 && d!="Illinois")  p <- add_line(p,il, "Illinois",       IL_COLOR, lwd=2,  sz=6)
    if(nrow(foc)>0) p <- add_line(p,foc,d,        CHI_COLOR,lwd=3,  sz=9)
    base_layout(p,ov$shapes,ov$annotations)
  }
  
  output$s_read_chart <- renderPlotly({ make_sum_chart("Reading") })
  output$s_math_chart <- renderPlotly({ make_sum_chart("Mathematics") })
  
  output$s_gradecompare_chart <- renderPlotly({
    d <- sel_district()
    rows <- list(
      list(label="Gr4 Reading",grade=4,subject="Reading"),
      list(label="Gr4 Math",grade=4,subject="Mathematics"),
      list(label="Gr8 Reading",grade=8,subject="Reading"),
      list(label="Gr8 Math",grade=8,subject="Mathematics")
    )
    df <- map_dfr(rows,function(r){
      chi <- get_score(d,r$subject,r$grade,2024)
      nat <- get_score("National public",r$subject,r$grade,2024)
      tibble(label=r$label,gap=chi-nat)
    })
    df <- df |> filter(!is.na(gap)) |> mutate(label=factor(label,levels=rev(rows|>map_chr(~.x$label))))
    if(nrow(df)==0) return(empty_chart())
    plot_ly(df,x=~gap,y=~label,type="bar",orientation="h",
            marker=list(color=if_else(df$gap>=0,K1C_GREEN,"#c53030")),
            text=~paste0(if_else(gap>=0,"+",""),round(gap,0)),textposition="outside",
            hovertemplate="%{y}: %{x:.0f} pts vs national<extra></extra>")|>
      layout(xaxis=list(title=paste0(d," − National Public (2024, pts)"),zeroline=TRUE,zerolinecolor="#718096",zerolinewidth=1.5,gridcolor=GRAY_LIGHT),
             yaxis=list(title=""),
             plot_bgcolor="white",paper_bgcolor="white",margin=list(l=90,r=30,t=10,b=40))|>config(displayModeBar=FALSE)
  })
  
  output$s_reform_details <- renderUI({
    sel <- s_ov()
    if(length(sel)==0) return(tags$p(style="font-size:11px;color:#a0aec0;","Select overlays above to see details."))
    rel <- Filter(function(r) r$label %in% sel,reforms)
    tagList(lapply(rel,function(r) tags$div(style="margin-bottom:10px;",
                                            tags$span(class=paste0("reform-chip chip-",r$level),r$label),
                                            tags$p(style="font-size:11px;color:#4a5568;margin:3px 0 0 0;",r$desc))))
  })
  
  output$s_kpi_row <- renderUI({
    d <- sel_district()
    gr <- as.integer(input$s_grade)
    gs <- function(j,s) {
      v <- naep|>filter(jurisdiction==j,subject==s,grade==gr,cat_value=="All students",year==2024)|>pull(score)
      if(length(v)==0) NA_real_ else round(v[1])
    }
    fmt  <- function(x) if(is.na(x)) "—" else as.character(x)
    hcell <- function(txt) tags$th(style="padding:5px 8px;font-size:10.5px;font-weight:600;color:#718096;border-bottom:1px solid #e2e8f0;",txt)
    cell  <- function(x,col) tags$td(style=paste0("padding:10px 8px;font-size:19px;font-weight:700;color:",col,
                                                  ";border-bottom:1px solid #e2e8f0;"),fmt(x))
    tags$table(style="width:100%;border-collapse:collapse;text-align:center;",
               tags$thead(
                 tags$tr(
                   tags$th(colspan="3",style="padding:6px;font-size:12px;font-weight:700;color:#4a5568;background:#F7F9F7;border-radius:4px 4px 0 0;","Reading"),
                   tags$th(colspan="3",style="padding:6px;font-size:12px;font-weight:700;color:#4a5568;background:#EDF2F7;border-radius:4px 4px 0 0;","Mathematics")
                 ),
                 tags$tr(
                   hcell("National Public"),hcell("Illinois"),hcell(d),
                   hcell("National Public"),hcell("Illinois"),hcell(d)
                 )
               ),
               tags$tbody(
                 tags$tr(
                   cell(gs("National public","Reading"),NAT_COLOR),
                   cell(gs("Illinois","Reading"),IL_COLOR),
                   cell(gs(d,"Reading"),CHI_COLOR),
                   cell(gs("National public","Mathematics"),NAT_COLOR),
                   cell(gs("Illinois","Mathematics"),IL_COLOR),
                   cell(gs(d,"Mathematics"),CHI_COLOR)
                 )
               )
    )
  })
  
  observeEvent(input$s_reset,{
    updateRadioButtons(session,"s_grade",selected=4)
    updateCheckboxGroupInput(session,"s_ov_fed",selected="COVID closures")
    updateCheckboxGroupInput(session,"s_ov_il",selected=character(0))
    updateCheckboxGroupInput(session,"s_ov_cps",selected=character(0))
  })
  
  # TRENDS / WHO'S LEFT BEHIND
  t_subs <- reactive({ naep|>filter(cat_label==input$t_category,jurisdiction==sel_district())|>pull(cat_value)|>unique()|>sort() })
  cat_display <- function(x) switch(x,"Race/Ethnicity"="Race","Econ. Disadvantage"="Economically Disadvantaged","Sex"="Gender",x)
  group_label <- function(x) if_else(x=="Hispanic","Latine",x)
  # Kids First palette: hex for Reading, ~50% alpha rgba for Math (70% for "All students")
  DEM_HEX <- c(
    "All students"="#303030",
    "White"="#ED9975","Black"="#009444","Hispanic"="#BFBCA3",
    "Asian/Pacific Islander"="#9ED0A7","American Indian/Alaska Native"="#8DC63F",
    "Two or more races"="#EFDA6B",
    "Identified as students with disabilities"="#ED9975","Not identified as students with disabilities"="#9ED0A7",
    "ELL"="#009444","Not ELL"="#9ED0A7",
    "Economically disadvantaged"="#BFBCA3","Not economically disadvantaged"="#EFDA6B",
    "Male"="#303030","Female"="#8DC63F")
  DEM_ALPHA <- c("All students"=0.7)
  hex2rgba <- function(hex,alpha) { rgbv <- grDevices::col2rgb(hex); sprintf("rgba(%d,%d,%d,%.2f)",rgbv[1],rgbv[2],rgbv[3],alpha) }
  group_color <- function(x,subject) {
    h <- unname(DEM_HEX[x]); if(is.na(h)) h <- "#999999"
    if(identical(subject,"Mathematics")) { a <- unname(DEM_ALPHA[x]); if(is.na(a)) a <- 0.5; hex2rgba(h,a) } else h
  }
  output$t_subgroup_ui <- renderUI({
    req(input$t_category!="All students")
    subs <- t_subs()
    dflt <- if("Black" %in% subs) "Black" else subs[1]
    selectInput("t_subgroup",NULL,choices=subs,selected=dflt)
  })
  output$t_peers_ui <- renderUI({
    selectizeInput("t_peers","Add individually:",choices=TUDA[TUDA!=sel_district()],
                   selected=NULL,multiple=TRUE,options=list(placeholder="Type to search..."))
  })
  observeEvent(input$t_peer_group,{
    if(input$t_peer_group!="None") {
      g <- PEER_GROUPS[[input$t_peer_group]]
      updateSelectizeInput(session,"t_peers",selected=g[g!=sel_district()])
    }
  })
  t_cv <- reactive({ if(input$t_category=="All students") "All students" else input$t_subgroup %||% t_subs()[1] })
  t_chi <- reactive({ naep|>filter(jurisdiction==sel_district(),subject==input$t_subject,grade==as.integer(input$t_grade),cat_value==t_cv()) })
  t_all <- reactive({
    peers <- input$t_peers %||% character(0)
    focus <- sel_district()
    j <- focus
    if(isTRUE(input$t_national))  j <- c(j,"National public")
    if(isTRUE(input$t_illinois))  j <- c(j,"Illinois")
    if(isTRUE(input$t_largecity)) j <- c(j,"Large city")
    j <- unique(c(j,peers))
    naep|>filter(jurisdiction %in% j,subject==input$t_subject,grade==as.integer(input$t_grade),cat_value==t_cv())
  })
  output$t_info_box <- renderUI({
    chi <- t_chi(); if(nrow(chi)==0) return(NULL)
    ibox(tags$b(paste0(sel_district()," · ")),input$t_subject," · Grade ",input$t_grade," · ",t_cv(),tags$br(),"Data: ",min(chi$year)," – ",max(chi$year))
  })
  output$t_kpi_row <- renderUI({
    d <- sel_district()
    gr <- as.integer(input$t_grade)
    
    if(input$t_category=="All students") {
      cur    <- function(s) get_score(d,s,gr,2024)
      delta  <- function(s,yr) {
        c <- cur(s); p <- get_score(d,s,gr,yr)
        if(is.na(c)||is.na(p)) NA_real_ else round(c-p)
      }
      fmtv   <- function(x) if(is.na(x)) "—" else as.character(round(x,0))
      fdelta <- function(x,label) {
        if(is.na(x)) return(tags$div(style="font-size:12px;color:#a0aec0;padding:3px 6px;",paste0("— ",label)))
        col <- if(x>0) "#276749" else if(x<0) "#c53030" else GRAY
        sign <- if(x>0) "+" else ""
        tags$div(style=paste0("font-size:12px;color:",col,";padding:3px 6px;"),paste0(sign,x," points ",label))
      }
      r_cur <- cur("Reading"); m_cur <- cur("Mathematics")
      hcell <- function(txt,bg) tags$th(style=paste0("padding:6px;font-size:12px;font-weight:700;color:#4a5568;background:",bg,
                                                     ";border-radius:4px 4px 0 0;"),txt)
      tags$div(style="margin-bottom:14px;",
               tags$div(style="font-size:13px;font-weight:600;color:#2d3748;margin-bottom:8px;",paste0(d,"'s Snapshot: Average Scale Scores")),
               tags$table(style="width:100%;border-collapse:collapse;text-align:center;",
                          tags$thead(tags$tr(hcell("Reading","#F7F9F7"),hcell("Mathematics","#EDF2F7"))),
                          tags$tbody(
                            tags$tr(
                              tags$td(style=paste0("padding:8px 6px;font-size:19px;font-weight:700;color:",K1C_GREEN,";"),fmtv(r_cur)),
                              tags$td(style=paste0("padding:8px 6px;font-size:19px;font-weight:700;color:",K1C_GREEN,";"),fmtv(m_cur))
                            ),
                            tags$tr(tags$td(fdelta(delta("Reading",2022),"vs. 2022")),   tags$td(fdelta(delta("Mathematics",2022),"vs. 2022"))),
                            tags$tr(tags$td(fdelta(delta("Reading",2019),"vs. 2019 (pre-COVID)")), tags$td(fdelta(delta("Mathematics",2019),"vs. 2019 (pre-COVID)"))),
                            tags$tr(tags$td(fdelta(delta("Reading",2014),"vs. 2014 (decade ago)")), tags$td(fdelta(delta("Mathematics",2014),"vs. 2014 (decade ago)")))
                          )
               )
      )
    } else {
      subs <- t_subs()
      if(length(subs)==0) return(NULL)
      gv <- function(s,sub) {
        v <- naep|>filter(jurisdiction==d,subject==s,grade==gr,cat_value==sub,year==2024)|>pull(score)
        if(length(v)==0) NA_real_ else round(v[1])
      }
      fmt   <- function(x) if(is.na(x)) "—" else as.character(x)
      hcell <- function(txt) tags$th(style="padding:5px 6px;font-size:10px;font-weight:600;color:#718096;border-bottom:1px solid #e2e8f0;",txt)
      cell  <- function(x) tags$td(style="padding:9px 6px;font-size:16px;font-weight:700;color:#2d3748;border-bottom:1px solid #e2e8f0;",fmt(x))
      rowlbl <- function(txt,col) tags$td(style=paste0("padding:9px 6px;font-size:11px;font-weight:600;color:",col,
                                                       ";text-align:left;border-bottom:1px solid #e2e8f0;"),txt)
      tags$div(style="margin-bottom:14px;",
               tags$div(style="font-size:13px;font-weight:600;color:#2d3748;margin-bottom:8px;",
                        paste0("2024 Snapshot: Average Scale Scores by ",cat_display(input$t_category))),
               tags$div(style="overflow-x:auto;",
                        tags$table(style="width:100%;border-collapse:collapse;text-align:center;",
                                   tags$thead(tags$tr(tags$th(style="padding:4px;",""),lapply(subs,hcell))),
                                   tags$tbody(
                                     tags$tr(rowlbl("Reading",K1C_GREEN), lapply(subs,function(s) cell(gv("Reading",s)))),
                                     tags$tr(rowlbl("Mathematics","#2d3748"), lapply(subs,function(s) cell(gv("Mathematics",s))))
                                   )
                        )
               )
      )
    }
  })
  output$t_chart_title_ui <- renderUI({ paste0(input$t_subject," · Grade ",input$t_grade," · ",t_cv()) })
  output$t_trend_chart <- renderPlotly({
    df <- t_all(); if(nrow(df)==0) return(empty_chart())
    peers <- input$t_peers %||% character(0)
    focus <- sel_district()
    cmap  <- c("National public"=NAT_COLOR,"Large city"="#a0aec0","Illinois"=IL_COLOR)
    cmap[[focus]] <- CHI_COLOR
    if(length(peers)>0) cmap <- c(cmap,setNames(PEER_COLS[seq_along(peers)],peers))
    p <- plot_ly()
    for(j in unique(df$jurisdiction)) {
      jdf <- df|>filter(jurisdiction==j); col <- cmap[[j]] %||% "#999"; bold <- j==focus
      p <- add_line(p,jdf,j,col,lwd=if(bold)3 else 1.5,sz=if(bold)9 else 5,
                    dash=if(j %in% c("National public","Large city","Illinois") && j!=focus) "dash" else "solid",open=!bold)
    }
    base_layout(p,
                list(list(type="rect",xref="x",yref="paper",x0=2019,x1=2022,y0=0,y1=1,fillcolor="#f6ad55",opacity=0.1,line=list(width=0))),
                list(list(xref="x",yref="paper",x=2020.5,y=0.97,text="COVID",showarrow=FALSE,font=list(color="#c05621",size=10))))
  })
  # MAIN CHART: every group's trend line over time, all in one plot. Click a
  # legend entry to hide that group, double-click to isolate one — native
  # Plotly legend behavior, no extra code needed.
  t_group_data <- reactive({
    req(input$t_category!="All students")
    naep|>filter(jurisdiction==sel_district(),subject==input$t_subject,grade==as.integer(input$t_grade),
                 cat_label==input$t_category,cat_value!="Information not available")
  })
  output$t_main_panel <- renderUI({
    req(input$t_category!="All students")
    cpanel(title=paste0(input$t_subject," · Grade ",input$t_grade," · ",cat_display(input$t_category)," by Year"),
           plotlyOutput("t_main_chart",height="440px"))
  })
  output$t_main_chart <- renderPlotly({
    raw <- t_group_data(); if(nrow(raw)==0) return(empty_chart())
    groups <- raw|>pull(cat_value)|>unique()|>sort()
    p <- plot_ly()
    for(g in groups) {
      gdf <- raw|>filter(cat_value==g)|>arrange(year)
      p <- p|>add_trace(data=gdf,x=~year,y=~score,type="scatter",mode="lines+markers",name=group_label(g),
                        line=list(color=group_color(g,input$t_subject),width=2.5),
                        marker=list(color=group_color(g,input$t_subject),size=7),
                        hovertemplate=paste0("<b>",group_label(g),"</b><br>%{x}: %{y:.0f}<extra></extra>"))
    }
    p|>layout(xaxis=list(title="",showgrid=FALSE,zeroline=FALSE),
              yaxis=list(title="Average Scale Score",showgrid=TRUE,gridcolor=GRAY_LIGHT,zeroline=FALSE),
              legend=list(orientation="h",y=-0.14,x=0,font=list(size=11)),
              plot_bgcolor="white",paper_bgcolor="white",margin=list(l=55,r=20,t=10,b=50))|>
      config(displayModeBar=FALSE)
  })
  
  
  
  observeEvent(input$wlb_race,{
    updateSelectInput(session,"t_subject",selected="Mathematics")
    updateRadioButtons(session,"t_grade",selected=4)
    updateSelectInput(session,"t_category",selected="Race/Ethnicity")
  })
  observeEvent(input$wlb_econ,{
    updateSelectInput(session,"t_subject",selected="Mathematics")
    updateRadioButtons(session,"t_grade",selected=4)
    updateSelectInput(session,"t_category",selected="Econ. Disadvantage")
  })
  observeEvent(input$wlb_gender,{
    updateSelectInput(session,"t_subject",selected="Reading")
    updateRadioButtons(session,"t_grade",selected=4)
    updateSelectInput(session,"t_category",selected="Sex")
  })
  observeEvent(input$t_reset,{
    updateSelectInput(session,"t_subject",selected="Mathematics")
    updateRadioButtons(session,"t_grade",selected=4)
    updateSelectInput(session,"t_category",selected="Race/Ethnicity")
    updateSelectInput(session,"t_subgroup",selected="Black")
    updateCheckboxInput(session,"t_national",value=TRUE)
    updateCheckboxInput(session,"t_illinois",value=TRUE)
    updateCheckboxInput(session,"t_largecity",value=FALSE)
    updateSelectInput(session,"t_peer_group",selected="None")
    updateSelectizeInput(session,"t_peers",selected=character(0))
  })
  
  # PEER
  p_years <- reactive({
    naep|>filter(subject==input$p_subject,grade==as.integer(input$p_grade),cat_value=="All students",jurisdiction %in% TUDA)|>
      group_by(year)|>summarise(n=n_distinct(jurisdiction))|>filter(n>=5)|>arrange(desc(year))|>pull(year)
  })
  output$p_year_ui <- renderUI({ yrs <- p_years(); selectInput("p_year",NULL,choices=yrs,selected=yrs[1]) })
  p_dist <- reactive({
    d <- sel_district()
    if("all" %in% input$p_filter) return(TUDA)
    keep <- character(0)
    if("similar" %in% input$p_filter) keep <- c(keep,SIMILAR_PEERS)
    if("high"    %in% input$p_filter) keep <- c(keep,HIGH_PERFORMERS)
    intersect(unique(c(keep,d)),TUDA)
  })
  p_dat <- reactive({
    req(input$p_year)
    df <- naep|>filter(subject==input$p_subject,grade==as.integer(input$p_grade),
                       year==as.integer(input$p_year),cat_value=="All students",jurisdiction %in% p_dist())
    switch(input$p_sort,"desc"=df|>arrange(desc(score)),"asc"=df|>arrange(score),"alpha"=df|>arrange(jurisdiction))
  })
  p_nat <- reactive({
    req(input$p_year)
    naep|>filter(jurisdiction=="National public",subject==input$p_subject,grade==as.integer(input$p_grade),year==as.integer(input$p_year),cat_value=="All students")|>pull(score)
  })
  p_rank <- reactive({
    req(input$p_year)
    df <- naep|>filter(subject==input$p_subject,grade==as.integer(input$p_grade),year==as.integer(input$p_year),cat_value=="All students",jurisdiction %in% TUDA)|>mutate(rank=rank(-score,ties.method="min"))
    list(rank=df|>filter(jurisdiction==sel_district())|>pull(rank),n=nrow(df))
  })
  output$p_info_box <- renderUI({
    req(input$p_year); r <- p_rank(); d <- sel_district()
    ibox(tags$b(paste0(d," · ")),input$p_subject," · Grade ",input$p_grade," · ",input$p_year,tags$br(),
         if(length(r$rank)>0) tagList(d," ranks ",tags$b(paste0(r$rank," of ",r$n))," TUDA districts"))
  })
  output$p_snapshot_title <- renderUI({ req(input$p_year); paste0(input$p_subject," · Grade ",input$p_grade," · All students · ",input$p_year) })
  output$p_why_box <- renderUI({
    d <- sel_district()
    ibox(tags$b("Why peer comparisons matter: "),
         paste0(d,"'s raw average can look strong or weak in isolation. Comparing it with large urban districts that serve similarly diverse, high-poverty populations — rather than the national average — shows whether ",d,"'s results are typical for a district like it, or an outlier."))
  })
  output$p_rank_title <- renderUI({ paste0(sel_district()," Ranking Over Time") })
  output$p_dot_chart <- renderPlotly({
    df <- p_dat(); nat <- p_nat(); d <- sel_district(); if(nrow(df)==0) return(empty_chart())
    dc <- case_when(df$jurisdiction==d~CHI_COLOR,df$jurisdiction %in% SIMILAR_PEERS&isTRUE(input$p_highlight)~ORANGE,TRUE~"#4A5568")
    xrange <- c(min(df$score,na.rm=T)-10,max(df$score,na.rm=T)+18)
    stem_shapes <- lapply(seq_len(nrow(df)),function(i) list(
      type="line",xref="x",yref="y",layer="below",
      x0=xrange[1],x1=df$score[i],y0=df$jurisdiction[i],y1=df$jurisdiction[i],
      line=list(color="#e2e8f0",width=2)))
    natshapes <- list()
    if(isTRUE(input$p_natline)&&length(nat)>0)
      natshapes <- list(list(type="line",xref="x",yref="paper",x0=nat,x1=nat,y0=0,y1=1,
                             line=list(color=NAT_COLOR,dash="dash",width=1.5)))
    p <- plot_ly(df,x=~score,y=~reorder(jurisdiction,score),type="scatter",mode="markers+text",showlegend=FALSE,
                 marker=list(color=dc,size=if_else(df$jurisdiction==d,16,12),
                             symbol=if_else(df$jurisdiction==d,"diamond","circle"),
                             line=list(color="white",width=1.5)),
                 text=~round(score,0),textposition="right",textfont=list(size=11,color="#2d3748"),
                 hovertemplate="<b>%{y}</b><br>%{x:.0f}<extra></extra>",cliponaxis=FALSE)
    p|>layout(xaxis=list(title="Average Scale Score",showgrid=TRUE,gridcolor=GRAY_LIGHT,zeroline=FALSE,range=xrange),
              yaxis=list(title="",tickfont=list(size=12,color="#2d3748"),showgrid=TRUE,gridcolor="#F1F5F4",gridwidth=1),
              shapes=c(stem_shapes,natshapes),
              plot_bgcolor="white",paper_bgcolor="white",margin=list(l=10,r=65,t=10,b=40))|>config(displayModeBar=FALSE)
  })
  output$p_legend_ui <- renderUI({
    nat <- p_nat()
    items <- list()
    if(isTRUE(input$p_natline)&&length(nat)>0)
      items <- c(items,list(tags$span(style=paste0("display:inline-flex;align-items:center;gap:5px;margin-right:16px;"),
                                      tags$span(style=paste0("width:16px;border-top:2px dashed ",NAT_COLOR,";display:inline-block;")),
                                      paste0("National public (",round(nat,0),")"))))
    if(isTRUE(input$p_highlight))
      items <- c(items,list(
        tags$span(style="display:inline-flex;align-items:center;gap:5px;margin-right:16px;",
                  tags$span(style=paste0("width:10px;height:10px;border-radius:50%;background:",ORANGE,";display:inline-block;")),
                  "Demographically similar"),
        tags$span(style="display:inline-flex;align-items:center;gap:5px;margin-right:16px;",
                  tags$span(style=paste0("width:11px;height:11px;background:",CHI_COLOR,";display:inline-block;transform:rotate(45deg);")),
                  sel_district())))
    if(length(items)==0) return(NULL)
    tags$div(style="font-size:11.5px;color:#4a5568;margin-top:6px;",items)
  })
  output$p_rank_chart <- renderPlotly({
    rdf <- naep|>filter(subject==input$p_subject,grade==as.integer(input$p_grade),cat_value=="All students",jurisdiction %in% TUDA)|>
      group_by(year)|>mutate(rank=rank(-score,ties.method="min"),n=n())|>ungroup()|>filter(jurisdiction==sel_district())
    if(nrow(rdf)==0) return(empty_chart())
    plot_ly(rdf,x=~year,y=~rank,type="scatter",mode="lines+markers",line=list(color=CHI_COLOR,width=2),marker=list(color=CHI_COLOR,size=7),
            customdata=~n,hovertemplate="%{x}: Rank %{y} of %{customdata}<extra></extra>")|>
      layout(xaxis=list(title="",tickformat="d",showgrid=FALSE,dtick=2),
             yaxis=list(title="Rank (1=highest)",autorange="reversed",showgrid=TRUE,gridcolor=GRAY_LIGHT,dtick=2),
             plot_bgcolor="white",paper_bgcolor="white",margin=list(l=60,r=20,t=5,b=30))|>config(displayModeBar=FALSE)
  })
  
  observeEvent(input$p_reset,{
    updateSelectInput(session,"p_subject",selected="Mathematics")
    updateRadioButtons(session,"p_grade",selected=4)
    updateRadioButtons(session,"p_sort",selected="desc")
    updateCheckboxInput(session,"p_natline",value=TRUE)
    updateCheckboxInput(session,"p_highlight",value=TRUE)
    updateCheckboxGroupInput(session,"p_filter",selected="all")
  })
}

shinyApp(ui,server)