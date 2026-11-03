from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .models import BusinessRequest
from .serializers import BusinessRequestSerializer
from .rag_service import answer_policy_question
from .ticket_service import generate_ticket_details


User = get_user_model()

VALID_STATUSES = ["Pending", "In Progress", "Completed"]
VALID_PRIORITIES = ["Low", "Medium", "High"]


def is_owner(user):
    """Only superusers are allowed to act as the Owner."""
    return bool(user and user.is_authenticated and user.is_superuser)


def get_user_requests(user):
    """Owners see all tickets; regular users see their own tickets."""
    if is_owner(user):
        return BusinessRequest.objects.all()
    return BusinessRequest.objects.filter(user=user)


def error_response(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data

        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        confirm_password = (
            data.get("confirm_password") or data.get("confirmPassword")
        )

        if not all(
            isinstance(value, str) and value.strip()
            for value in (username, email, password, confirm_password)
        ):
            return error_response(
                "Username, email, password, and password confirmation are required."
            )

        username = username.strip()
        email = email.strip().lower()

        if password != confirm_password:
            return error_response("Passwords do not match.")

        if User.objects.filter(username__iexact=username).exists():
            return error_response("This username is already taken.")

        if User.objects.filter(email__iexact=email).exists():
            return error_response("An account with this email already exists.")

        try:
            validate_email(email)
            validate_password(password)
        except DjangoValidationError as exc:
            return error_response(" ".join(exc.messages))

        full_name = (data.get("name") or "").strip()
        first_name = (data.get("first_name") or "").strip()
        last_name = (data.get("last_name") or "").strip()

        if full_name and not first_name:
            parts = full_name.split(maxsplit=1)
            first_name = parts[0]
            if len(parts) > 1 and not last_name:
                last_name = parts[1]

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=False,
            is_superuser=False,
        )

        return Response(
            {
                "message": "Account created successfully. You can now sign in.",
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        identifier = request.data.get("username") or request.data.get("email")
        password = request.data.get("password")

        if not isinstance(identifier, str) or not identifier.strip() or not password:
            return error_response("Username/email and password are required.")

        identifier = identifier.strip()
        username = identifier

        if "@" in identifier:
            matching_user = User.objects.filter(email__iexact=identifier).first()
            if matching_user:
                username = matching_user.username

        user = authenticate(
            request=request,
            username=username,
            password=password,
        )

        if user is None:
            return error_response(
                "Invalid username/email or password.",
                status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return error_response(
                "This account is inactive.",
                status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.username,
                "name": user.get_full_name() or user.username,
                "role": "Owner" if is_owner(user) else "User",
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.auth:
            request.auth.delete()
        return Response({"message": "Logged out successfully."})


class BusinessRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        queryset = get_user_requests(request.user)

        if id is not None:
            ticket = get_object_or_404(queryset, id=id)
            return Response(BusinessRequestSerializer(ticket).data)

        # Search across all requested fields.
        search_query = request.query_params.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(category__icontains=search_query)
                | Q(resolution__icontains=search_query)
            )

        status_filter = request.query_params.get("status", "").strip()
        if status_filter:
            if status_filter not in VALID_STATUSES:
                return error_response(
                    "Invalid status. Choose Pending, In Progress, or Completed."
                )
            queryset = queryset.filter(status=status_filter)

        priority_filter = request.query_params.get("priority", "").strip()
        if priority_filter:
            if priority_filter not in VALID_PRIORITIES:
                return error_response(
                    "Invalid priority. Choose Low, Medium, or High."
                )
            queryset = queryset.filter(priority=priority_filter)

        category_filter = request.query_params.get("category", "").strip()
        if category_filter:
            queryset = queryset.filter(category__iexact=category_filter)

        # Optional Owner filter: match ticket submitter username.
        user_filter = request.query_params.get("username", "").strip()
        if user_filter and is_owner(request.user):
            queryset = queryset.filter(user__username__icontains=user_filter)

        allowed_ordering = {
            "title", "-title",
            "priority", "-priority",
            "status", "-status",
            "category", "-category",
            "created_at", "-created_at",
            "updated_at", "-updated_at",
        }
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering not in allowed_ordering:
            ordering = "-created_at"

        queryset = queryset.order_by(ordering, "-id")

        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginator.page_size_query_param = "page_size"
        paginator.max_page_size = 50

        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BusinessRequestSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if is_owner(request.user):
            return error_response(
                "Only regular Users can create AI requests.",
                status.HTTP_403_FORBIDDEN,
            )

        issue = request.data.get("issue")
        if not isinstance(issue, str) or not issue.strip():
            return error_response("Please describe your issue.")

        try:
            generated = generate_ticket_details(issue.strip())
        except Exception:
            import traceback
            traceback.print_exc()
            return error_response(
                "The AI ticket generator is unavailable. Check that Ollama is running and try again.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not isinstance(generated, dict):
            return error_response(
                "The AI generated an invalid ticket.",
                status.HTTP_502_BAD_GATEWAY,
            )

        required_fields = ["title", "description", "category", "priority"]
        if any(
            not isinstance(generated.get(field), str)
            or not generated[field].strip()
            for field in required_fields
        ):
            return error_response(
                "The AI generated incomplete ticket details.",
                status.HTTP_502_BAD_GATEWAY,
            )

        priority = generated["priority"].strip().capitalize()
        if priority not in VALID_PRIORITIES:
            priority = "Medium"

        ticket_data = {
            "title": generated["title"].strip()[:200],
            "description": generated["description"].strip(),
            "category": generated["category"].strip()[:50],
            "priority": priority,
            "status": "Pending",
        }

        serializer = BusinessRequestSerializer(data=ticket_data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_502_BAD_GATEWAY,
            )

        ticket = serializer.save(user=request.user)

        return Response(
            {
                "message": f"Your ticket #{ticket.id} has been raised successfully.",
                "ticket": BusinessRequestSerializer(ticket).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def put(self, request, id=None):
        return self._update_ticket(request, id, partial=False)

    def patch(self, request, id=None):
        return self._update_ticket(request, id, partial=True)

    def _update_ticket(self, request, id, partial):
        if not is_owner(request.user):
            return error_response(
                "Only the Owner can update tickets.",
                status.HTTP_403_FORBIDDEN,
            )

        if id is None:
            return error_response("A ticket ID is required.")

        ticket = get_object_or_404(BusinessRequest, id=id)
        data = request.data.copy()

        # Never allow the Owner to transfer a ticket to another user.
        data.pop("user", None)
        data.pop("user_id", None)

        if "status" in data and data["status"] not in VALID_STATUSES:
            return error_response("Invalid ticket status.")

        if "priority" in data and data["priority"] not in VALID_PRIORITIES:
            return error_response("Invalid ticket priority.")

        # The frontend uses resolution. Accept solution as an alias too.
        if "solution" in data and "resolution" not in data:
            data["resolution"] = data.pop("solution")

        serializer = BusinessRequestSerializer(
            ticket,
            data=data,
            partial=partial,
        )

        if serializer.is_valid():
            serializer.save(user=ticket.user)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None):
        if not is_owner(request.user):
            return error_response(
                "Only the Owner can delete tickets.",
                status.HTTP_403_FORBIDDEN,
            )

        if id is None:
            return error_response("A ticket ID is required.")

        ticket = get_object_or_404(BusinessRequest, id=id)
        ticket.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = get_user_requests(request.user)

        categories = (
            queryset.values("category")
            .annotate(count=Count("id"))
            .order_by("category")
        )

        return Response(
            {
                "role": "Owner" if is_owner(request.user) else "User",
                "total_requests": queryset.count(),
                "pending_requests": queryset.filter(status="Pending").count(),
                "in_progress_requests": queryset.filter(status="In Progress").count(),
                "completed_requests": queryset.filter(status="Completed").count(),
                "high_priority_requests": queryset.filter(priority="High").count(),
                "category_distribution": list(categories),
            }
        )


class PolicyChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if is_owner(request.user):
            return error_response(
                "Policy AI is available on the User dashboard.",
                status.HTTP_403_FORBIDDEN,
            )

        question = request.data.get("question", "")
        if not isinstance(question, str) or not question.strip():
            return error_response("Please provide a policy question.")

        try:
            result = answer_policy_question(question.strip())
            return Response(result)
        except FileNotFoundError:
            return error_response(
                "The company policy PDF could not be found.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            import traceback
            traceback.print_exc()
            return error_response(
                "The policy assistant encountered an error. Check that Ollama is running and the model is available.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )