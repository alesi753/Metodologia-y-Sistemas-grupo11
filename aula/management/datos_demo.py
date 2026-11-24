# Datos de la cursada de ejemplo que carga `python manage.py cargar_demo`.
# Las fechas son desplazamientos en días desde hoy (negativo = pasado), así la
# demo siempre tiene clase de hoy, próximas fechas y entregas vencidas.

CLAVE = 'demo1234'
CARRERA = 'TUP'

ADMIN = 'admin-demo'
ALUMNO_DEMO = '50231'

# (legajo, nombre, apellido)
ALUMNOS = [
    ('50231', 'Lucía', 'Fernández'),
    ('50232', 'Tomás', 'Gutiérrez'),
    ('50233', 'Valentina', 'Acosta'),
    ('50234', 'Mateo', 'Romero'),
]

PROFESORES = [
    ('20101', 'Marta', 'Ríos'),
    ('20102', 'Julián', 'Paz'),
    ('20103', 'Andrés', 'Molina'),
    ('20104', 'Carolina', 'Sosa'),
    ('20105', 'Diego', 'Herrera'),
    ('20106', 'Sofía', 'Luna'),
]


# Atajos para escribir contenidos. `extra` admite:
#   completado: días desde hoy en que el alumno demo lo completó
#   intentos:   intentos del alumno demo (por defecto 1)
#   borrador:   True si todavía no está publicado
def texto(clave, titulo, secciones, **extra):
    cuerpo = {'secciones': [{'titulo': t, 'texto': x} for t, x in secciones]}
    return {'clave': clave, 'formato': 'texto', 'titulo': titulo, 'cuerpo': cuerpo, **extra}


def cuestionario(clave, titulo, preguntas, **extra):
    cuerpo = {
        'aprobacion': 0.7,
        'preguntas': [
            {'enunciado': e, 'opciones': opciones, 'correcta': correcta}
            for e, opciones, correcta in preguntas
        ],
    }
    return {'clave': clave, 'formato': 'cuestionario', 'titulo': titulo, 'cuerpo': cuerpo, **extra}


def practica(clave, titulo, consigna, entregables, formatos='.pdf, .zip', **extra):
    cuerpo = {'consigna': consigna, 'entregables': entregables, 'formatos_aceptados': formatos}
    return {'clave': clave, 'formato': 'practica', 'titulo': titulo, 'cuerpo': cuerpo, **extra}


# Una entrada por cátedra.
#   horarios: (días después del día de hoy, desde, hasta). 0 = hoy.
#   clases:   se ubican en los horarios; las primeras `clases_pasadas` caen antes de hoy.
#   eventos:  (tipo, título, días desde hoy, clave del contenido o None)
#   avisos:   (legajo del autor, días desde hoy, título, cuerpo)
CATEDRAS = [
    {
        'materia': 'Gestión de Desarrollo de Software',
        'profesores': ['20101', '20102'],
        'horarios': [(0, '18:30', '20:00'), (2, '18:30', '21:00')],
        'unidades': [
            {
                'orden': 1, 'titulo': 'Planificación y gestión de un producto de software',
                'conceptos': ['Alcance', 'Estimación', 'Backlog', 'Hitos', 'Riesgos'],
                'apertura': -35, 'limite': -10,
                'contenidos': [
                    texto('gds-planificar', 'Qué es planificar un producto', [
                        ('Alcance', 'El alcance define qué entra en el producto y, sobre todo, qué queda '
                                    'afuera. Un alcance explícito evita que el proyecto crezca sin control.'),
                        ('Hitos', 'Un hito es un punto verificable del cronograma: una entrega, una demo o '
                                  'una aprobación. Sin hitos no hay forma de saber si vamos atrasados.'),
                    ], completado=-30),
                    texto('gds-estimacion', 'Estimación ágil', [
                        ('Puntos de historia', 'Miden el esfuerzo relativo de una historia comparada '
                                               'con otras, no horas.'),
                        ('Velocidad', 'Son los puntos completados por iteración, promediados en las '
                                      'últimas iteraciones.'),
                        ('Planning Poker', 'Sirve para estimar en grupo sin que la primera opinión '
                                           'condicione al resto.'),
                    ], completado=-25),
                    cuestionario('gds-autoevaluacion', 'Autoevaluación Unidad 1', [
                        ('¿Cuál de estos es un hito?',
                         ['Escribir código', 'Demo aprobada por el cliente', 'Una reunión semanal'], 1),
                        ('La velocidad del equipo se mide en…',
                         ['Horas trabajadas', 'Puntos completados por iteración', 'Commits por día'], 1),
                        ('Un alcance explícito sirve para…',
                         ['Evitar que el proyecto crezca sin control', 'Reemplazar la estimación',
                          'Definir el stack'], 0),
                    ], completado=-20, intentos=2),
                    practica('gds-plan', 'Plan de proyecto',
                             'Armá el plan de proyecto del producto que eligió tu grupo: alcance, '
                             'backlog inicial estimado e hitos.',
                             ['Documento PDF del plan', 'Backlog en planilla o captura del tablero'],
                             completado=-12),
                    practica('gds-riesgos', 'Matriz de riesgos',
                             'Identificá cinco riesgos del proyecto, estimá probabilidad e impacto y '
                             'proponé una mitigación para cada uno.',
                             ['Matriz de riesgos en PDF'], formatos='.pdf',
                             completado=-7),
                ],
            },
            {
                'orden': 2, 'titulo': 'El producto, el proceso y el proyecto',
                'conceptos': ['Ciclo de vida', 'Modelos de proceso', 'Métricas'],
                'apertura': -10, 'limite': 10,
                'contenidos': [
                    texto('gds-modelos', 'Modelos de proceso', [
                        ('Cascada', 'Etapas secuenciales: cada una arranca cuando termina la anterior. '
                                    'Sirve cuando los requisitos son estables.'),
                        ('Iterativo e incremental', 'El producto crece en iteraciones cortas que '
                                                    'entregan algo usable y se ajustan con feedback.'),
                    ], completado=-4),
                    cuestionario('gds-ciclo', 'Ciclo de vida', [
                        ('¿Qué es el ciclo de vida de un producto?',
                         ['Las etapas desde la idea hasta su retiro', 'Un diagrama de clases',
                          'El cronograma de un sprint'], 0),
                        ('¿Qué modelo conviene con requisitos cambiantes?',
                         ['Cascada', 'Iterativo e incremental'], 1),
                    ], completado=-2, intentos=2),
                    practica('gds-relevamiento', 'Relevamiento de requisitos',
                             'Entrevistá a un usuario del producto y escribí diez historias de usuario '
                             'con sus criterios de aceptación.',
                             ['Minuta de la entrevista', 'Historias de usuario en PDF']),
                    texto('gds-metricas', 'Métricas de proceso', [
                        ('Lead time', 'Tiempo desde que se pide algo hasta que está en producción.'),
                    ], borrador=True),
                ],
            },
            {
                'orden': 3, 'titulo': 'Gestión de la configuración',
                'conceptos': ['Versionado', 'Ramas', 'Releases'],
                'apertura': 9, 'limite': 30,
                'contenidos': [
                    texto('gds-versionado', 'Versionado con git', [
                        ('Commits', 'Un commit es una foto del proyecto con un mensaje que explica '
                                    'el porqué del cambio.'),
                        ('Ramas', 'Permiten trabajar en paralelo sin pisar el trabajo de otros.'),
                    ]),
                    cuestionario('gds-ramas', 'Estrategias de ramas', [
                        ('¿Para qué sirve la rama develop en git flow?',
                         ['Integrar el trabajo antes de una versión', 'Guardar versiones viejas'], 0),
                    ], borrador=True),
                ],
            },
            {
                'orden': 99, 'titulo': 'Fe de erratas', 'corrige': [1],
                'contenidos': [
                    texto('gds-errata', 'Corrección: cómo se calcula la velocidad', [
                        ('Qué cambió', 'En «Estimación ágil» decía que la velocidad se calcula con la '
                                       'última iteración. Se promedia con las últimas tres.'),
                    ]),
                ],
            },
        ],
        'clases_pasadas': 3,
        'primera_clase': 8,
        'clases': [
            {'titulo': 'Alcance y backlog', 'unidad': 1, 'contenidos': ['gds-planificar'],
             'resumen': 'Cómo recortar el alcance y armar un backlog priorizado.'},
            {'titulo': 'Estimación con Planning Poker', 'unidad': 1, 'contenidos': ['gds-estimacion'],
             'resumen': 'Taller de estimación sobre el backlog de cada grupo.', 'ausente': True},
            {'titulo': 'Riesgos del proyecto', 'unidad': 1, 'contenidos': ['gds-riesgos'],
             'resumen': 'Identificación de riesgos y armado de la matriz.'},
            {'titulo': 'Modelos de proceso', 'unidad': 2, 'contenidos': ['gds-modelos', 'gds-ciclo'],
             'resumen': 'Cascada contra iterativo, con ejemplos de proyectos reales.',
             'link': 'https://meet.google.com/gds-hoy-demo'},
            {'titulo': 'Taller de relevamiento', 'unidad': 2, 'contenidos': ['gds-relevamiento'],
             'resumen': 'Práctica de entrevistas en grupos.',
             'link': 'https://meet.google.com/gds-taller-demo'},
            {'titulo': 'Consulta antes del parcial', 'unidad': 2,
             'resumen': 'Repaso de las unidades 1 y 2.'},
        ],
        'eventos': [
            ('entrega', 'Plan de proyecto', -10, 'gds-plan'),
            ('entrega', 'Matriz de riesgos', -10, 'gds-riesgos'),
            ('entrega', 'Relevamiento de requisitos', 10, 'gds-relevamiento'),
            ('parcial', 'Primer parcial', 14, None),
            ('presentacion', 'Demo del producto', 28, None),
            ('final', 'Mesa de final', 45, None),
        ],
        'avisos': [
            ('20101', 0, 'La clase de hoy también va por Meet',
             'El link ya está cargado en la clase del día. Se toma asistencia al ingresar.'),
            ('20102', -3, 'Publicamos una fe de erratas',
             'Corregimos cómo se calcula la velocidad del equipo. Está en la unidad Fe de erratas.'),
        ],
    },
    {
        'materia': 'Metodología de Sistemas II',
        'profesores': ['20103'],
        'horarios': [(1, '18:30', '21:30')],
        'unidades': [
            {
                'orden': 1, 'titulo': 'Patrones de diseño',
                'conceptos': ['Strategy', 'Observer', 'Facade', 'Adapter'],
                'apertura': -20, 'limite': 12,
                'contenidos': [
                    texto('ms-patrones', 'Patrones de comportamiento', [
                        ('Strategy', 'Encapsula algoritmos intercambiables detrás de una misma interfaz.'),
                        ('Observer', 'Un objeto avisa a sus suscriptores cuando cambia, sin conocerlos.'),
                    ], completado=-6),
                    cuestionario('ms-strategy', 'Strategy y Observer', [
                        ('¿Qué patrón usarías para elegir el cálculo de envío según el método?',
                         ['Observer', 'Strategy', 'Singleton'], 1),
                        ('Las señales de Django son un ejemplo de…',
                         ['Observer', 'Adapter', 'Facade'], 0),
                    ]),
                    practica('ms-secuencia', 'Diagramas de secuencia',
                             'Modelá con diagramas de secuencia dos casos de uso de tu proyecto.',
                             ['Diagramas en PDF', 'Fuente editable (.puml o .drawio)'],
                             formatos='.pdf, .puml, .drawio'),
                ],
            },
            {
                'orden': 2, 'titulo': 'Arquitectura en capas',
                'conceptos': ['Capas', 'MVC', 'MVT de Django'],
                'apertura': 12, 'limite': 35,
                'contenidos': [
                    texto('ms-capas', 'De MVC a MVT', [
                        ('MVT', 'En Django la vista cumple el rol del controlador y el template el '
                                'de la vista.'),
                    ]),
                ],
            },
        ],
        'clases_pasadas': 2,
        'primera_clase': 7,
        'clases': [
            {'titulo': 'Patrones creacionales', 'unidad': 1,
             'resumen': 'Factory Method y Builder con ejemplos en Python.'},
            {'titulo': 'Strategy y Observer en Django', 'unidad': 1, 'contenidos': ['ms-patrones'],
             'resumen': 'Dónde aparecen estos patrones dentro del framework.'},
            {'titulo': 'Facade y Adapter', 'unidad': 1, 'contenidos': ['ms-strategy'],
             'resumen': 'Cómo aislar un servicio externo detrás de una interfaz propia.',
             'link': 'https://meet.google.com/ms2-facade-demo'},
            {'titulo': 'Taller de casos de uso', 'unidad': 1, 'contenidos': ['ms-secuencia'],
             'resumen': 'Cada grupo presenta sus casos de uso.'},
        ],
        'eventos': [
            ('presentacion', 'Taller de casos de uso', 8, None),
            ('entrega', 'Diagramas de secuencia', 11, 'ms-secuencia'),
            ('parcial', 'Parcial de patrones', 18, None),
        ],
        'avisos': [
            ('20103', -2, 'Grupos para el taller de casos de uso',
             'Armen grupos de cuatro y avisen por mail antes del viernes.'),
        ],
    },
    {
        'materia': 'Legislación',
        'profesores': ['20104'],
        'horarios': [(0, '20:00', '22:00')],
        'unidades': [
            {
                'orden': 1, 'titulo': 'Derecho informático',
                'conceptos': ['Contratos informáticos', 'Propiedad intelectual', 'Licencias'],
                'apertura': -30, 'limite': -5,
                'contenidos': [
                    texto('leg-contratos', 'Contratos informáticos', [
                        ('Qué son', 'Acuerdos cuyo objeto es un bien o servicio informático: '
                                    'desarrollo, licencia, mantenimiento o hosting.'),
                        ('Licencias', 'El software se licencia, no se vende: el autor conserva '
                                      'la propiedad intelectual.'),
                    ], completado=-20),
                    cuestionario('leg-cuestionario-1', 'Cuestionario Unidad 1', [
                        ('Al comprar un programa, el usuario adquiere…',
                         ['La propiedad del código', 'Una licencia de uso'], 1),
                    ], completado=-9),
                ],
            },
            {
                'orden': 2, 'titulo': 'Protección de datos personales',
                'conceptos': ['Ley 25.326', 'Datos sensibles', 'Habeas data'],
                'apertura': -5, 'limite': 8,
                'contenidos': [
                    texto('leg-datos', 'La Ley 25.326', [
                        ('Consentimiento', 'Tratar datos personales requiere el consentimiento libre, '
                                           'expreso e informado del titular.'),
                        ('Habeas data', 'Acción para acceder, rectificar o suprimir los datos propios.'),
                    ], completado=-1),
                    cuestionario('leg-cuestionario-2', 'Cuestionario Unidad 2', [
                        ('¿Qué acción permite pedir la rectificación de los datos propios?',
                         ['Amparo', 'Habeas data', 'Habeas corpus'], 1),
                        ('La religión de una persona es un dato…',
                         ['Público', 'Sensible', 'Anónimo'], 1),
                    ]),
                ],
            },
        ],
        'clases_pasadas': 2,
        'primera_clase': 11,
        'clases': [
            {'titulo': 'Licencias de software', 'unidad': 1,
             'resumen': 'Licencias privativas y libres: GPL, MIT y Apache.'},
            {'titulo': 'Datos personales', 'unidad': 2, 'contenidos': ['leg-datos'],
             'resumen': 'Principios de la Ley 25.326.'},
            {'titulo': 'Repaso para el parcial integrador', 'unidad': 2,
             'contenidos': ['leg-cuestionario-2'],
             'resumen': 'Clase de consulta. Traer dudas del cuestionario de la Unidad 2.'},
            {'titulo': 'Delitos informáticos', 'unidad': 2,
             'resumen': 'La Ley 26.388 y los delitos más comunes.'},
        ],
        'eventos': [
            ('entrega', 'Cuestionario Unidad 1', -5, 'leg-cuestionario-1'),
            ('entrega', 'Cuestionario Unidad 2', 1, 'leg-cuestionario-2'),
            ('parcial', 'Parcial integrador', 3, None),
        ],
        'avisos': [
            ('20104', -1, 'Temas del parcial integrador',
             'Entran las unidades 1 y 2. El cuestionario de la Unidad 2 es buena preparación. Traer DNI.'),
        ],
    },
    {
        'materia': 'Programación IV',
        'profesores': ['20105', '20106'],
        'horarios': [(3, '18:30', '20:00'), (4, '18:30', '21:00')],
        'unidades': [
            {
                'orden': 1, 'titulo': 'APIs REST con Django',
                'conceptos': ['Serialización', 'Verbos HTTP', 'Autenticación'],
                'apertura': -40, 'limite': -14,
                'contenidos': [
                    texto('p4-rest', 'Diseño de una API REST', [
                        ('Recursos', 'Cada URL nombra un recurso; los verbos HTTP dicen qué se hace con él.'),
                        ('Códigos de estado', '201 al crear, 404 si no existe, 400 si el pedido es inválido.'),
                    ], completado=-30),
                    practica('p4-tp3', 'TP3: API REST',
                             'Implementá una API REST con alta, baja, modificación y listado de un '
                             'recurso, con tests.',
                             ['Link al repositorio', 'README con cómo correrla'], formatos='.zip',
                             completado=-15),
                ],
            },
            {
                'orden': 2, 'titulo': 'Calidad del código',
                'conceptos': ['TDD', 'Dobles de prueba', 'Cobertura'],
                'apertura': -3, 'limite': 20,
                'contenidos': [
                    texto('p4-tdd', 'Introducción a TDD', [
                        ('El ciclo', 'Rojo, verde, refactor: primero un test que falla, después el '
                                     'código mínimo para que pase y al final se limpia.'),
                    ]),
                    practica('p4-kata', 'Kata: calculadora con TDD',
                             'Resolvé la kata de la calculadora de strings escribiendo primero los tests.',
                             ['Link al repositorio con el historial de commits'], formatos='.zip'),
                ],
            },
        ],
        'clases_pasadas': 2,
        'primera_clase': 9,
        'clases': [
            {'titulo': 'Autenticación por token', 'unidad': 1,
             'resumen': 'Sesiones contra tokens y cuándo conviene cada uno.'},
            {'titulo': 'Testing: TDD y dobles de prueba', 'unidad': 2, 'contenidos': ['p4-tdd'],
             'resumen': 'Primer vistazo a la Unidad 2.', 'link': 'https://meet.google.com/p4-tdd-demo'},
            {'titulo': 'Kata en clase', 'unidad': 2, 'contenidos': ['p4-kata'],
             'resumen': 'Resolvemos la kata en parejas.', 'link': 'https://meet.google.com/p4-kata-demo'},
            {'titulo': 'Cobertura y refactor', 'unidad': 2,
             'resumen': 'Cómo leer un reporte de cobertura sin obsesionarse con el número.'},
        ],
        'eventos': [
            ('entrega', 'TP3: API REST', -14, 'p4-tp3'),
            ('parcial', 'Primer parcial', 2, None),
            ('entrega', 'Kata: calculadora con TDD', 9, 'p4-kata'),
            ('final', 'Mesa de final', 24, None),
        ],
        'avisos': [
            ('20105', -5, 'Consultas antes del parcial',
             'El lunes a las 18:00 hay consulta en el aula 12, media hora antes de la clase.'),
            ('20106', -1, 'Repositorio base de la kata',
             'Subimos el repositorio base con la estructura de tests. Clónenlo antes de la clase.'),
        ],
    },
]
