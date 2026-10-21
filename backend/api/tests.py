import json
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings, Client
from src.token_budget import InputBudgetError
from .services import ServiceBusy

TOKEN = 't'*48


@override_settings(RAG_API_TOKEN=TOKEN,ALLOWED_HOSTS=['testserver'],DEBUG=False)
class DocumentationTests(SimpleTestCase):
    def test_documentation_and_schema_are_public_and_do_not_initialize_rag(self):
        with patch('api.services.resources') as resources:
            page = self.client.get('/api/v1/docs/')
            schema = self.client.get('/api/v1/openapi.json')
        self.assertEqual(page.status_code,200)
        self.assertEqual(schema.status_code,200)
        self.assertNotIn(TOKEN,page.content.decode())
        self.assertNotIn(TOKEN,schema.content.decode())
        self.assertIn('persistAuthorization: false',page.content.decode())
        self.assertIn('validatorUrl: null',page.content.decode())
        resources.assert_not_called()

    def test_schema_matches_routes_authentication_and_request_contracts(self):
        from django.urls import resolve
        from .contracts import QueryRequest, SearchRequest
        document = self.client.get('/api/v1/openapi.json').json()
        self.assertEqual(document['openapi'],'3.1.0')
        self.assertEqual(document['security'],[{'BearerAuth':[]}])
        self.assertEqual(document['paths']['/api/v1/health/']['get']['security'],[])
        for route, method in {'health/':'get','categories/':'get','rag/search/':'post','rag/query/':'post'}.items():
            path = '/api/v1/'+route
            self.assertIn(method,document['paths'][path])
            self.assertIn(method,resolve(path).func.view_class.http_method_names)
        for model in (QueryRequest,SearchRequest):
            self.assertEqual(document['components']['schemas'][model.__name__],model.model_json_schema())
        for model in ('QueryResponse','SearchResponse'):
            self.assertIn('tiempos_segundos',document['components']['schemas'][model]['properties'])
        responses = document['paths']['/api/v1/rag/query/']['post']['responses']
        self.assertTrue({'200','400','401','413','415','422','429','502','503'} <= responses.keys())

    def test_documented_examples_validate_against_runtime_contracts(self):
        from .contracts import QueryRequest, SearchRequest
        from .documentation import (HealthResponse, CategoriesResponse, SearchResponse,
                                    QueryResponse, ErrorResponse)
        models = {'health/':HealthResponse, 'categories/':CategoriesResponse,
                  'rag/search/':SearchResponse, 'rag/query/':QueryResponse}
        document = self.client.get('/api/v1/openapi.json').json()
        for route, model in models.items():
            method = 'post' if route.startswith('rag/') else 'get'
            operation = document['paths']['/api/v1/'+route][method]
            for status, response in operation['responses'].items():
                for name, example in response['content']['application/json']['examples'].items():
                    with self.subTest(route=route, status=status, example=name):
                        (model if status == '200' else ErrorResponse).model_validate(example['value'])
            if method == 'post':
                request_model = SearchRequest if route == 'rag/search/' else QueryRequest
                for example in operation['requestBody']['content']['application/json']['examples'].values():
                    request_model.model_validate(example['value'])
        query = document['paths']['/api/v1/rag/query/']['post']
        for example in query['responses']['200']['content']['application/json']['examples'].values():
            value = example['value']
            labels = value['respuesta_documental']['citas']
            self.assertEqual(set(labels), {source['id'] for source in value['fuentes']})
            for label in labels:
                self.assertIn('['+label+']',value['respuesta_documental']['respuesta'])

    def test_swagger_assets_work_with_debug_disabled_and_unknown_files_are_blocked(self):
        for name, mime in [('swagger-ui.css','text/css'),('swagger-ui-bundle.js','application/javascript'),
                           ('swagger-ui-standalone-preset.js','application/javascript')]:
            with self.subTest(name=name):
                response = self.client.get('/api/v1/docs/assets/'+name)
                self.assertEqual(response.status_code,200)
                self.assertTrue(response['Content-Type'].startswith(mime))
                self.assertGreater(len(b''.join(response.streaming_content)),100)
                response.close()
        self.assertEqual(self.client.get('/api/v1/docs/assets/LICENSE').status_code,404)

    def test_schema_references_resolve_to_components(self):
        document = self.client.get('/api/v1/openapi.json').json()
        def walk(value):
            if isinstance(value,dict):
                if '$ref' in value:
                    prefix = '#/components/schemas/'
                    self.assertTrue(value['$ref'].startswith(prefix))
                    self.assertIn(value['$ref'][len(prefix):],document['components']['schemas'])
                for child in value.values():walk(child)
            elif isinstance(value,list):
                for child in value:walk(child)
        walk(document)


@override_settings(RAG_API_TOKEN=TOKEN,ALLOWED_HOSTS=['testserver'],DEBUG=False)
class ControllerTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.headers = {'HTTP_AUTHORIZATION':'Bearer '+TOKEN}
        self.result = {'state':'OK_PIDE_ACLARACION','classification':{'categoria':'redes'},
            'documentary_output':{'estado':'respondida','respuesta':'Regla documentada. [F1]','citas':['F1'],'limitacion':''},
            'latency_seconds':1.2,'rag':{'timings':{'semantic_search_seconds':.15,'bm25_seconds':.01,'total_seconds':1.2},'catalog':{'F1':{'chunk_id':'chunk','metadata':{
                'source':'redes/manual_redes.pdf','pages':[1],'section':'Conexión'}}}},
            'raw_output':'private-rejected-output','execution_error':None,
            'classification_trace':{'credentials':'private-secret'}}

    def query(self,value=None,**kwargs):
        return self.client.post('/api/v1/rag/query/',data=json.dumps(value or {'pregunta':'¿Qué reviso en mi red?'}),content_type='application/json',**(kwargs or self.headers))

    def test_health_is_liveness_without_network_or_model(self):
        with patch('api.services.resources') as resources:
            response=self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['input_token_limit'],1000)
        resources.assert_not_called()

    def test_categories_are_exactly_the_seven_existing_values(self):
        response=self.client.get('/api/v1/categories/',**self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(set(response.json()['categorias']),{'hardware','software','redes','cuentas','seguridad','acceso','otros'})

    def test_missing_wrong_or_cookie_credentials_never_invoke_service(self):
        with patch('api.services.run_query') as service:
            for auth in ('','Basic abc','Bearer wrong'):
                self.assertEqual(self.query(HTTP_AUTHORIZATION=auth).status_code,401)
            self.client.cookies['sessionid']='fake-session'
            self.assertEqual(self.query(HTTP_AUTHORIZATION='').status_code,401)
        service.assert_not_called()

    @override_settings(RAG_API_TOKEN='')
    def test_missing_configuration_is_closed(self):
        with patch('api.services.run_query') as service:
            self.assertEqual(self.query().status_code,503)
        service.assert_not_called()

    def test_success_exposes_only_accepted_answer_and_cited_sources(self):
        with patch('api.services.run_query',return_value=self.result) as service:
            response=self.query()
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertEqual(data['estado'],'OK_PIDE_ACLARACION')
        self.assertEqual(data['tiempos_segundos'],self.result['rag']['timings'])
        self.assertEqual(data['fuentes'][0]['id'],'F1')
        self.assertNotIn('private',response.content.decode())
        self.assertNotIn('raw_output',data)
        self.assertEqual(service.call_args.args[0],'¿Qué reviso en mi red?')

    def test_missing_empty_wrong_type_or_extra_fields_are_rejected(self):
        with patch('api.services.run_query') as service:
            for value in ({'pregunta':' '},{'pregunta':12},{'pregunta':None},{'pregunta':'q','mode':'mock'},['q'],{'owner_id':'other'}):
                self.assertEqual(self.query(value).status_code,400)
        service.assert_not_called()

    def test_invalid_json_unicode_and_media_type(self):
        for body in (b'{',b'\xff'):
            response=self.client.post('/api/v1/rag/query/',body,content_type='application/json',**self.headers)
            self.assertEqual(response.status_code,400)
        response=self.client.post('/api/v1/rag/query/','text',content_type='text/plain',**self.headers)
        self.assertEqual(response.status_code,415)

    def test_payload_size_limit(self):
        response=self.client.post('/api/v1/rag/query/',b'x'*17000,content_type='application/json',**self.headers)
        self.assertEqual(response.status_code,413)

    def test_budget_and_embedding_limit_map_to_422(self):
        with patch('api.services.run_query',side_effect=InputBudgetError('private-input')):
            response=self.query()
        self.assertEqual(response.status_code,422)
        self.assertNotIn('private',response.content.decode())

    def test_quota_failure_maps_to_429_and_retry_after(self):
        result={**self.result,'state':'ERROR_TECNICO','documentary_output':None,
                'execution_error':'HTTP 429: espera requerida de 238.25 s fuera del presupuesto de reintentos.'}
        with patch('api.services.run_query',return_value=result):response=self.query()
        self.assertEqual(response.status_code,429)
        self.assertEqual(response.headers['Retry-After'],'239')
        self.assertNotIn('execution_error',response.json())

    def test_invalid_provider_response_is_502(self):
        with patch('api.services.run_query',return_value={**self.result,'state':'ERROR_FORMATO'}):response=self.query()
        self.assertEqual(response.status_code,502)

    def test_service_exception_and_corrupted_index_are_not_client_errors(self):
        for exc in (RuntimeError('private-secret'),ValueError('private-index')):
            with patch('api.services.run_query',side_effect=exc):response=self.query()
            self.assertEqual(response.status_code,503)
            self.assertNotIn('private',response.content.decode())

    def test_busy_response_is_retryable(self):
        with patch('api.services.run_query',side_effect=ServiceBusy()):response=self.query()
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.headers['Retry-After'],'2')

    def test_documentary_limits_are_successful_business_results(self):
        for state in ('aclaracion','parcial','evidencia_insuficiente'):
            result={**self.result,'documentary_output':{'estado':state,'respuesta':'Límite documentado.','citas':[],'limitacion':'Falta evidencia.'}}
            with patch('api.services.run_query',return_value=result):response=self.query()
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['fuentes'],[])

    def test_search_does_not_call_generation(self):
        with patch('api.services.search',return_value={'corpus_id':'corpus','pasajes':[],'tiempos_segundos':{'bm25_seconds':.01}}) as search,patch('api.services.run_query') as generate:
            response=self.client.post('/api/v1/rag/search/',data=json.dumps({'pregunta':'Wi-Fi','categoria':'redes'}),content_type='application/json',**self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['tiempos_segundos'],{'bm25_seconds':.01})
        search.assert_called_once_with('Wi-Fi','redes')
        generate.assert_not_called()

    def test_search_unknown_category_is_rejected(self):
        response=self.client.post('/api/v1/rag/search/',data=json.dumps({'pregunta':'q','categoria':'inventada'}),content_type='application/json',**self.headers)
        self.assertEqual(response.status_code,400)

    def test_method_and_unknown_route_return_json(self):
        response=self.client.get('/api/v1/rag/query/',**self.headers)
        self.assertEqual(response.status_code,405)
        self.assertEqual(response.json()['error']['code'],'method_not_allowed')
        self.assertEqual(self.client.get('/api/v1/no-existe/').json()['error']['code'],'not_found')


@override_settings(RAG_API_TOKEN=TOKEN)
class ServiceTests(SimpleTestCase):
    def test_question_too_long_is_rejected_before_model_or_credentials(self):
        from api.services import run_query
        with patch('api.services.retriever') as load:
            with self.assertRaises(InputBudgetError):run_query('token '*2500,'id')
        load.assert_not_called()

    def test_search_service_preserves_retrieval_timings(self):
        from api.services import search
        from unittest.mock import Mock
        retriever=Mock(corpus_id='test')
        retriever.retrieve.return_value=([],{'semantic_search_seconds':.2,'bm25_seconds':.01})
        with patch('api.services.retriever',return_value=retriever):
            result=search('Error 403')
        self.assertEqual(result['tiempos_segundos'],retriever.retrieve.return_value[1])
        self.assertEqual(result['pasajes'],[])

    def test_per_process_slot_blocks_concurrent_work(self):
        from api.services import _work_slot,run_query
        _work_slot.acquire()
        try:
            with self.assertRaises(ServiceBusy):run_query('No puedo entrar.','id')
        finally:
            _work_slot.release()

    def test_model_initialization_error_releases_slot(self):
        from api.services import _work_slot,run_query
        with patch('api.services.retriever',side_effect=RuntimeError('bad-index')):
            with self.assertRaises(RuntimeError):run_query('No puedo entrar.','id')
        self.assertTrue(_work_slot.acquire(blocking=False))
        _work_slot.release()
