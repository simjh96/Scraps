from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import re
import os
import datetime
import pandas as pd

class Dart():
    """
    기업 1 개당 1 instance
    공시 정보 확인 및 특정 정보 내역 df로 추출 및 정리

    - 무결성이 보장됨
    있는 정보는 확인할 필요 없음(틀리지 않음)
    없는 정보는 확인 해봐야함
    
    ex) 주주명부는 [누가 무엇을 얼마나] 형식으로 
    되어 있지 않다면 가져 올 수 없음

    - get은 정말 get 밖에 안해줌
    
    - WebDriverWait 또는
    time.sleep를 조정해서 감독 가능... 
    <page_list의 경우 refresh 전에 감지 할때가 있어서 sleep 넣는게 좋음>

    - 사업보고서 크롤링 코드 미비
    사업보고서가 나오는 기업의 경우 감사보고서 정보가 아주 예전일 수 있음!

    - 파크시스템즈 -> 파크시스템스(개선 알고리즘 구현 필요)

    - 전환청구권 행사의 경우 dfs[1] == 본문 으로 취급
    dummy + 정정보도에 대해 filter 필요

    - KISLINE의 대표 업체명 upchae_rap 에 넣어야함

    - 기한 설정 함수 만들어야함

    - 엑셀에 적을때 fillna 해주자

    - mul_col_index_fix
    greedy 해서 내용까지 잡아 먹을 수 있음
    SH_list 주로 짤림
    
    - try error로 wrap 해줘서 사용

    - 확인코드
    k = list(self.dfs_dic.keys())
    self.dfs_dic[k[0]]
    """

    #0계층
    def __init__(self, upmoo_name_clean, rep_of_upchae = '기입안됨', specifics=True):
        #variables
        self.upmoo_name_clean = upmoo_name_clean
        self.rep_of_upchae = rep_of_upchae
        self.url_dic = {'dart_root':'https://dart.fss.or.kr'
                        ,'dart_search':'https://dart.fss.or.kr/dsab001/main.do'
                        }
        self.dfs_dic = {}   # deli:df   ['dart_name', 'house_info', 'shares_info', 'notice_info', 'audit_info']
        self.delimeters = []
        self.dfs = []   # 1 df 씩

        self.candidate_counter = 0  #자꾸 에러나서 하드 코딩...
        self.specifics = specifics

        #actions
        self.start_driver()
        self.total_scan()
        
        self.driver.quit()
    
    
    #1계층
    def start_driver(self):
        #chrome driver dir check
        #go to dart
        try:
            self.driver = webdriver.Chrome("./chromedriver.exe")
        except:
            print("시스템>>> 현재 디렉토리: {}".format(os.getcwd()))
            print("시스템>>> does this directory contain right version of chromedriver.exe? (Y)/(N): ")
            inp = input()
            if inp == 'N':
                print("시스템>>> 크롬드라이버가 있는 위치 입력...")
                os.chdir(input())
            self.driver = webdriver.Chrome("./chromedriver.exe")

        print("시스템>>> 드라이버를 실행 합니다...")

    def total_scan(self):
        """
        #해당 종목의 dart 정보 모두 스캔해
        #total_history_df = concat(주요사항,지분,거래소)
        #전환청구권 이외의 주권 및 리픽싱 관련 변동사항이 없는지 여기서 확인 필요
        #지분관련 공시는 게시자가 많음으로
        #관심pef 이름만 넣는걸로...
        """
        print("시스템>>> {} 의 전체 공시자료를 살펴봅니다.".format(self.upmoo_name_clean))
        
        self.driver.get(self.url_dic['dart_search'])

        #get and save
        self.save_dfs_dic(self.get_house_info())
        self.save_dfs_dic(self.get_shares_info())
        self.save_dfs_dic(self.get_notice_info())
        self.save_dfs_dic(self.get_audit_info())
        print("시스템>>> {} 의 모든 공시 사항 확인이 완료 되었습니다.".format(self.upmoo_name_clean))
        print("시스템>>> openpyxl을 통해 엑셀에 자동 기입을 추천합니다.")
        
    #2계층
     
    def get_house_info(self):
        """
        get and return {deli:df,deli:df,...}
        """
        print("시스템>>> {} 의 거래소 공시 사항을 확인합니다.".format(self.upmoo_name_clean))

        #search
        self.basic_settings()

        self.driver.find_element('id','publicTypeButton_09').click()
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'total_choice9')))
        self.driver.find_element('id','total_choice9').click()
        self.driver.find_element('id','searchpng').click()
        time.sleep(1)
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'page_list')))

        #결과가 없다면 끝내
        page_list = self.get_page_list()
        if len(page_list) == 0:
            print("시스템>>> {} 의 거래소 공시 사항이 없습니다.".format(self.upmoo_name_clean))
            return dict()

        #거래소 공시중 이미 시가에 반영된 사항들 filter
        #지분 사항 및 평가대상 증권과 관련 없는 내용들 filter
        #filtering
        filter_list = ['본점소재지변경','단일판매ㆍ공급계약체결','정기주주총회결과','매출액또는손익구조30%'
                        ,'감사보고서제출','신규시설투자','주주총회소집결의','임시주주총회결과'
                        ,'주주명부폐쇄기간또는기준일설정','기업설명회(IR)개최','주주총회집중일개최사유신고'
                        ,'타법인주식및출자증권취득결정','유상증자또는주식관련사채등의청약결과(자율공시)'
                        ,'본점소재지변경','주식명의개서정지(주주명부폐쇄)','행사가액결정','단일판매ㆍ공급계약해지'
                        ,'연결재무제표기준영업(잠정)실적','유형자산취득결정','영업(잠정)실적','유형자산처분결정'
                        ,'영업실적등에대한전망','장래사업ㆍ경영계획','기준가산정','반기검토(감사)보고서제출'
                        ,'기타경영사항']
        filter_series = pd.Series(filter_list)

        page_list = page_list.loc[page_list.loc[:,'보고서명'].apply(lambda x: not any(filter_series.apply(lambda y: y in x)))]

        rights_info = self.get_rights_info(page_list)
        claim_info = self.get_claim_info(page_list)
        refixing_info = self.get_refix_info(page_list)

        #출력할 df 들 저장
        result = {}
        result['house_page_list'] = page_list
        result['house_rights_info'] = rights_info
        result['house_claim_info'] = claim_info[0]
        result['house_balance_info'] = claim_info[1]
        result['house_refixing_info'] = refixing_info
        return result
                        
    def get_shares_info(self):
        print("시스템>>> {} 의 지분 공시 사항을 확인합니다.".format(self.upmoo_name_clean))
        
        #search
        self.basic_settings()

        self.driver.find_element('id','publicTypeButton_04').click()
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'total_choice4')))
        self.driver.find_element('id','total_choice4').click()
        self.driver.find_element('id','searchpng').click()
        time.sleep(1)
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'page_list')))

        #결과가 없다면 끝내
        page_list = self.get_page_list()
        if len(page_list) == 0:
            print("시스템>>> {} 의 지분 공시 사항이 없습니다.".format(self.upmoo_name_clean))
            return dict()

        if self.specifics:
            specific_info = self.get_specific_info()
        else:
            specific_info = pd.DataFrame(['정보 가져오려면','설정을 바꾸세요'],['설정','안함'])
        #출력할 df 들 저장
        result = {}
        result['shares_page_list'] = page_list
        result['shares_specific_info'] = specific_info
        return result

    def get_notice_info(self):
        print("시스템>>> {} 의 주요 공시 사항을 확인합니다.".format(self.upmoo_name_clean))

        #search
        self.basic_settings()

        self.driver.find_element('id','publicTypeButton_02').click()
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'total_choice2')))
        self.driver.find_element('id','total_choice2').click()
        self.driver.find_element('id','searchpng').click()
        time.sleep(1)
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'page_list')))

        #결과가 없다면 끝내
        page_list = self.get_page_list()
        if len(page_list) == 0:
            print("시스템>>> {} 의 주요사항 공시 사항이 없습니다.".format(self.upmoo_name_clean))
            return dict()

        #출력할 df 들 저장
        result = {}
        result['notice_page_list'] = page_list
        return result

    def get_audit_info(self):
        """
        search upchae_name and return [list of reports, [most recent BS, IS, Capital Change, Shareholder List]]
        """
        print("시스템>>> {} 의 감사보고 사항을 확인합니다.".format(self.upmoo_name_clean))

        #search
        self.basic_settings()

        self.driver.find_element('id','publicTypeButton_06').click()
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'total_choice6')))
        self.driver.find_element('id','total_choice6').click()
        self.driver.find_element('id','searchpng').click()
        time.sleep(1)
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'page_list')))

        #결과가 없다면 끝내
        page_list = self.get_page_list()
        if len(page_list) == 0:
            print("시스템>>> {} 의 감사보고서 공시 사항이 없습니다.".format(self.upmoo_name_clean))
            return dict()

        #첫 FS 에서 [list of reports, most recent BS, IS, Capital Change, Shareholder List] filtering 
        viewer_main =  self.url_dic['dart_root'] + page_list.loc[0,'links']
        rcpno,dcmno = self.get_rcp_dcm(viewer_main)

        self.driver.get(self.viewer_url(rcpno,dcmno))
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'section-1')))

        #공시자료 전체 검색
        dfs = pd.read_html(self.driver.page_source)
        audit_info = self.audit_filter(dfs)

        #출력할 df 들 저장
        #아주 예전인 경우 사업보고서 참조
        result = {}
        result['audit{}_page_list'.format(rcpno[:8])] = page_list
        result['audit{}_BS_info'.format(rcpno[:8])] = audit_info[0]
        result['audit{}_IS_info'.format(rcpno[:8])] = audit_info[1]
        result['audit{}_CC_info'.format(rcpno[:8])] = audit_info[2]
        result['audit{}_CF_info'.format(rcpno[:8])] = audit_info[3]
        result['audit{}_SH_info'.format(rcpno[:8])] = audit_info[4]
        return result


    #3계층

    def basic_settings(self):
        print("시스템>>> {} 검색을 위한 Dart 검색 환경을 세팅합니다.".format(self.upmoo_name_clean))

        #search setting
        self.driver.get(self.url_dic['dart_search'])
        candidate_list = self.select_upchae_name()
        self.save_dfs_dic(candidate_list)

        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'date7')))
        self.driver.find_element('id','date7').click()
        self.driver.find_element_by_xpath('//*[@id="maxResultsCb"]/option[4]').click()

    def get_rights_info(self, page_list):
        """
        권리 행사에 관한 사항들 df
        """
        print("시스템>>> {} 의 권리 행사 관련 정보를 수집합니다.".format(self.upmoo_name_clean))
        return page_list.loc[page_list.loc[:,'보고서명'].apply(lambda x: '권행사' in x),:]

    def get_claim_info(self, page_list, balance=True):
        """
        청구 관련 정보들 수집
        현재 : '전환청구권행사' 로만 검색 중
        무결성을 위한 balance 도 제공

        return [df_claim, df_balance]
        """
        print("시스템>>> {} 의 전환청구권 행사 관련 정보를 수집합니다.".format(self.upmoo_name_clean))

        claim_dfs = page_list.loc[page_list.loc[:,'보고서명'].apply(lambda x: '전환청구권행사' in x),:]
        df_claim = pd.DataFrame()
        df_balance = pd.DataFrame()

        for i in claim_dfs.index:
            self.driver.get(self.url_dic['dart_root'] + claim_dfs.loc[i,'links'])
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'ifrm')))
            time.sleep(0.2)

            self.driver.switch_to.frame('ifrm')
            dfs = pd.read_html(self.driver.page_source)

            #정정보도인 경우 dfs[1] -> dfs[4]로 밀림
            body_df_idx = 1
            if '정정일자' in dfs[0].to_string():
                body_df_idx = 4

            #전체 내역인 dfs[0]은 필요 없고 일별만 parsing
            df_claim = pd.concat([df_claim, self.mul_col_idx_fix(dfs[body_df_idx])])

            #유효성 검사를 위해 잔액 확인
            #전환가능 주식수*전환가 + 기 SIGMGA(발행 주식수*전환가) = 항상 Total 과 같아야함
            if balance:
                df_balance = pd.concat([df_balance,self.mul_col_idx_fix(dfs[body_df_idx+1])])

        return [df_claim, df_balance]

    def get_refix_info(self, page_list):
        """
        #조정 관련 내역 정보 수집
        #현재는 전환청구권만 가능
        """
        print("시스템>>> {} 의 청구권 조정 관련 정보를 수집합니다".format(self.upmoo_name_clean))
        print("시스템>>> 청구권 조정 관련 기능은 구현 되지 않았습니다 ㅠㅠ...".format(self.upmoo_name_clean))

        pass 
    
    def get_specific_info(self):
        """
        #게시자 이름 받아서 하는편이 수월함
        #세부변동내역만 가져옴

        return df
        """
        print("시스템>>> {} 의 주식등의대량보유상황 세부정보를 수집합니다.".format(self.upmoo_name_clean))

        #전체검색 -> 주식등의대량보유상황보고서(일반)만 검색
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'total_choice4')))
        self.driver.find_element('id','total_choice4').click()
        time.sleep(0.5)
        self.driver.find_element('id','publicType20').click()
        time.sleep(0.5)
        self.driver.find_element('id','searchpng').click()
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'page_list')))

        page_list = self.get_page_list()
        if len(page_list) == 0:
            print("시스템>>> {} 의 주식등의대량보유상황 공시 사항이 없습니다.".format(self.upmoo_name_clean))
            return dict()

        #누구의 history를 보고 싶은지 설정
        pef_name = input(str(set(page_list.loc[:,'제출인']))+' 중 검색 대상 제출인을 골라주세요')
        specific_df_concat = pd.DataFrame()

        for i in range(len(page_list)):
            if page_list.loc[i,'제출인'] == pef_name:
                self.driver.get(self.url_dic['dart_root'] + page_list.loc[i,'links'])
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="north"]/div[2]/ul/li[1]/a/img')))
                time.sleep(1)

                viewer_main =  self.url_dic['dart_root'] + page_list.loc[i,'links']
                rcp, dcm = self.get_rcp_dcm(viewer_main)
                self.driver.get(self.viewer_url(rcp, dcm))
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'section-1')))

                dfs = pd.read_html(self.driver.page_source)

                #세부변동내역만 필요

                specific_df = self.specific_filter(dfs)

                #이중 인덱싱 제거(세부변동내역 페이지는 어떤 종목이든 이중 인덱싱 존재)
                specific_df = self.mul_col_idx_fix(specific_df)
                specific_df_concat = pd.concat([specific_df_concat, specific_df])


        return specific_df_concat

    def get_page_list(self):
        """
        page_list 가져옴 빈칸인 경우에는 blank df

        get Dart's 'page-list' of all searched results
        """
        print("시스템>>> 검색 내용의 page_list를 수집합니다.".format(self.upmoo_name_clean))

        page_list = pd.DataFrame()
        src = BeautifulSoup(self.driver.page_source,'lxml')
        page_list_src = src.find('div',{'class':'page_list'})
        for i in range(len(page_list_src.find_all('input',{'onclick':re.compile(r'search.+')})) - 1):
            self.driver.find_element_by_xpath('//*[@id="listContents"]/div[2]/input[{}]'.format(i+1)).click()
            time.sleep(1)
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'table_list')))
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'page_list')))
            
            src = BeautifulSoup(self.driver.page_source,'lxml')
            
            html_tb = src.findChildren('div','table_list')[0]

            #links
            links = []

            articles = html_tb.find_all(lambda x: x.has_attr('href') and x.has_attr('id'))
            for j in range(len(articles)):
                links.append(articles[j]['href'])
                # print('시스템>>>links에 {}가 삽입됨'.format(articles[j]['href']))

            page_list = pd.concat([page_list, 
                            pd.concat([pd.Series(links,name='links')
                            , pd.read_html(str(html_tb))[0]]
                            ,axis=1)])

        return page_list

    def audit_filter(self, dfs):
        """
        '전체 공시 사항의 전체 표'를 입력받아
        '부채총계'가 들어가는 표 == 재무상태표
        그 다음 표 == 손익계산서
        그 다음 표 == 자본변동표

        필요한 information == [누가[주주, 주주명, 구분], 얼마나[지분율, 지분비율], 무엇을[보통주]]
        return [BS,IS,CC,SH_list] or empty df
        """
        print("시스템>>> audit 공시 자료 전체를 확인중입니다... ")
        #재무상태표 필터어
        bs_str = r'부[\s\t\n]*채[\s\t\n]*총[\s\t\n]*계'

        #주주명부 필터어
        who = [r'주[\s\t\n]*주[\s\t\n]*',r'구[\s\t\n]*분[\s\t\n]*']
        what = [r'보[\s\t\n]*통[\s\t\n]*주[\s\t\n]*',r'주[\s\t\n]*식[\s\t\n]*']
        how_much = [r'지[\s\t\n]*분[\s\t\n]*']

        ban_words_list = [r'종[\s\t\n]*목[\s\t\n]*',r'피[\s\t\n]*투[\s\t\n]*자[\s\t\n]*',r'취[\s\t\n]*득',r'원[\s\t\n]*가']

        bs_df = None

        for i in range(len(dfs)):
            #bs
            if len(re.findall(bs_str,dfs[i].to_string())) != 0:
                bs_df = self.mul_col_idx_fix(dfs[i]).apply(lambda x: x.fillna('0'))
                
                #손익계산서, 자본변동표, 현금흐름표는 뒤에 세개 들고오자
                rest_dfs = []
                counter = 1
                while counter < 100:
                    if len(dfs[i + counter]) > 4:
                        rest_dfs.append(self.mul_col_idx_fix(dfs[i + counter]).apply(lambda x: x.fillna('0')))
                        if len(rest_dfs) > 2:
                            break
                    counter += 1
            
            yes_words = []
            for yes in [who, what, how_much]:
                yess = []
                for _ in yes:
                    yess.append((len(re.findall(_,dfs[i].to_string())) != 0))
                yes_words.append(any(yess))

            ban_words = []
            for ban_word in ban_words_list:
                ban_words.append((len(re.findall(ban_word,dfs[i].to_string())) != 0))
        
            if (all(yes_words) and (not any(ban_words))):
                holders_df = self.mul_col_idx_fix(dfs[i].apply(lambda x: x.fillna('0')))
                break

        #이거 앞줄로 가면... 에러 나던데... 왜지?
        if str(bs_df) == 'None':
            bs_df, rest_dfs, holders_df = pd.DataFrame(), [pd.DataFrame(),pd.DataFrame(), pd.DataFrame()], pd.DataFrame()

        return [bs_df,rest_dfs[0],rest_dfs[1],rest_dfs[2],holders_df]


    #4계층

    def select_upchae_name(self):
        """
        현실... : 제일 위에 값
        이상적 : max(['기타법인','코스닥시장','유가증권시장'])

        선택 업체 정보 반환으로 맞는지 확인
        return {'candidates': df}
        """
        print("시스템>>> 업체를 선택중입니다.")

        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'btnOpenFindCrp')))
        # print('이거 하고 끊어지는것 같은데?')
        self.driver.find_element_by_id('btnOpenFindCrp').click()

        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'x-window-mc')))
        time.sleep(0.5)
        self.driver.find_elements_by_id('textCrpNm')[1].send_keys(self.basic_strip(self.upmoo_name_clean, space=False))
        self.driver.find_elements_by_id('textCrpNm')[1].send_keys(Keys.ENTER)
        time.sleep(1)

        #검색 목록 확인
        src = BeautifulSoup(self.driver.page_source,'lxml')
        result = pd.read_html(src.find_all('div',{'id':'ext-comp-1002'})[0].prettify())
        result[0].loc[0,:] = result[1].loc[0,:].to_list()

        #검색 결과 없으면 종료
        if result[0].iloc[0,0] == '일치하는 회사명이 없습니다.':
            print("시스템>>> Dart에는 {} 의 공시 자료가 없습니다.".format(self.upmoo_name_clean))
            print("시스템>>> 검색을 종료합니다.")
            self.driver.quit()
            return dict()

        #선택 및 확인
        self.driver.find_elements_by_id('checkCorpSelect')[0].click()
        self.driver.find_element_by_xpath('//*[@id="corpListContents"]/div/fieldset/div[3]/a[1]/img').click()
        time.sleep(0.5)

        if self.candidate_counter == 0:
            print("시스템>>> {} 업종의 '{}'(대표자: {},KISLINE: {})가 선택되었습니다.".format(result[0].loc[0,'업종명'],result[0].loc[0,'회사명'],result[0].loc[0,'대표자명'],self.rep_of_upchae))
            self.candidate_counter += 1

        self.candidates = result[0]

        return {'candidates': result[0]}

    def check_null(self, deli, df):
        """
        input : deli, df
        """
        content = (len(df) > 0)
        print("시스템>>> {} 의 자료 여부가 {} 입니다.".format(deli, content))
        return content

    def save_dfs_dic(self, _dic):
        """
        dic0 == {deli:df,deli:df,...} of 'need to save'들 받아서 
        하나씩 편성 여부 확인 후 저장
        """
        for deli in list(_dic.keys()):    
            if not (deli in list(self.dfs_dic.keys())):
                self.delimeters.append(deli)
                self.dfs.append(_dic[deli])
                self.dfs_dic[deli] = _dic[deli]
                print("시스템>>> {} 정보 저장됨.".format(deli))

    def viewer_url(self,rcpno,dcmno):
        return 'http://dart.fss.or.kr/report/viewer.do?rcpNo={}&dcmNo={}&eleId=1&offset=0&length=0&dtd=dart3.xsd'.format(rcpno,dcmno)

    def mul_col_idx_fix(self, df):
        """
        erase overlapping columns until no overlapping neighbor appears
        case of 'mul_col1 in columns and mul_col2 at body', not considered
        multi-index solution needs to be added...
        """
        # print("시스템>>> erasing multi_column ")
        if type(df.columns)==pd.core.indexes.multi.MultiIndex:
            df.columns = pd.DataFrame(df.columns).loc[:,0].apply(lambda x: x[-1])
        else:
            for i in range(len(df.index)):
                if df.iloc[i,0] == df.iloc[i+1,0]:
                    continue
                else:
                    #if first row of body is indeed a body... break
                    if i == 0:
                        break
                    df_body = df.loc[i+1:,:]
                    df_body.columns = df.loc[i,:]
                    df = df_body
                    break
        return df

    def get_rcp_dcm(self, viewer_main):
        """
        input: report article's viewer_main_url
        return [rcpno, dcmno]
        """
        self.driver.get(viewer_main)
        time.sleep(0.5)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="north"]/div[2]/ul/li[1]/a/img')))
        #안에 내용까지 쉬어야 하나???
        time.sleep(1)

        src = BeautifulSoup(self.driver.page_source,'lxml')
        print('시스템>>>소스코드 확보됨')
        rcpno, dcmno = re.findall("'[0-9]+'",src.find_all('a',{'href':'#download'})[0]['onclick'])
        rcpno, dcmno = rcpno[1:-1], dcmno[1:-1]
        print('시스템>>>rcpnos에 {}가 삽입됨'.format(rcpno))
        print('시스템>>>dcmnos에 {}가 삽입됨'.format(dcmno))

        return [rcpno, dcmno]

    def basic_strip(self, with_zoo, space=True):
        result = re.sub(r'\(.+?\)','',with_zoo.replace('㈜','')).strip()
        if space:
            return result
        else:
            return result.replace('\s','')

    def specific_filter(self, dfs):
        """
        return filtered df for specifics search
        """
        print('시스템>>>세부변동 내역 정보 조회 및 필터링 중...')
        distinct_col = ['성명(명칭)', '생년월일 또는사업자등록번호 등', '변동일*', '취득/처분방법', '주식등의종류', '변동전', '증감','변동후', '취득/처분단가**', '비 고']

        for df in dfs:
            for i in distinct_col:
                flag = 1
                if not (i in df.to_string()):
                    flag = 0
                    break
            if flag:
                specific_df = df
                return specific_df


