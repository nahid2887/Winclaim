import json
import re
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from Chat.models import ChatSession, ChatMessage,FlaggedMessage, UserClaimUpload
from rest_framework import status
from Chat.serializers import ChatMessageSerializer, FlaggedMessageSerializer,ChatSessionSerializer, UserClaimUploadSerializer
from .gpt_utils import stream_gpt_response  # your wrapper using `Message` dataclass
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from reportlab.lib.colors import HexColor, black, white
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from uuid import UUID
# from .serializers import ClaimAnalysisSerializer
from .AI_claim_document_upload import main
import tempfile
import os 
from  .AIclaim import get_benji_response, create_session_history
from django.http import FileResponse
from io import BytesIO
from accounts.permissions import IsChatAccessAllowed, IsDashboardAccessAllowed  # Import custom permissions
# class ChatStreamAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#     @swagger_auto_schema(
#         operation_summary="Register a new user",
#         operation_description="Signup using full name, email, mobile, and password.",
#         request_body=ChatMessageSerializer,
#         responses={
#             201: openapi.Response("User created successfully"),
#             400: openapi.Response("Bad request (validation errors)")
#         }
#     )

#     def post(self, request):
#         from .models import ChatSession, ChatMessage
#         from .serializers import ChatMessageSerializer
#         from .gpt_utils import stream_gpt_response  # your stream function

#         session_id = request.data.get("session_id")
#         user_input = request.data.get("content")

#         if not user_input:
#             return Response({"error": "Message content is required."}, status=400)

#         # Validate or create session
#         if session_id:
#             try:
#                 session_uuid = UUID(session_id)  # Ensure it's a valid UUID
#                 session = ChatSession.objects.get(session_id=session_uuid, user=request.user)
#             except (ValueError, ChatSession.DoesNotExist):
#                 return Response({"error": "Invalid or unauthorized session ID."}, status=404)
#         else:
#             # Create new session if no session_id provided
#             session = ChatSession.objects.create(user=request.user)

#         # Save user's message
#         user_msg = ChatMessage.objects.create(
#             session=session,
#             user=request.user,
#             sender="User",
#             content=user_input
#         )

#         # Collect previous messages (if any)
#         db_messages = session.messages.order_by("timestamp")

#         def stream_response():
#             full_response = ""
#             try:
#                 for chunk in stream_gpt_response(user_input, db_messages):
#                     delta = chunk["choices"][0].get("delta", {}).get("content", "")
#                     full_response += delta
#                     yield f"data: {delta}\n\n"

#                 # Save AI response
#                 ai_msg = ChatMessage.objects.create(
#                     session=session,
#                     user=request.user,
#                     sender="AI",
#                     content=full_response
#                 )

#                 # Final message
#                 final_payload = {
#                     "session_id": str(session.session_id),
#                     "user_message": ChatMessageSerializer(user_msg).data,
#                     "ai_message": ChatMessageSerializer(ai_msg).data
#                 }
#                 yield f"data: [DONE] {json.dumps(final_payload)}\n\n"

#             except Exception as e:
#                 yield f"data: [ERROR] {str(e)}\n\n"

#         return StreamingHttpResponse(stream_response(), content_type='text/event-stream')


# class ChatStreamAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     @swagger_auto_schema(
#         operation_summary="Send a new message",
#         operation_description="Send a message and receive an AI response with all session messages.",
#         request_body=ChatMessageSerializer,
#         responses={
#             200: openapi.Response("Message processed successfully"),
#             400: openapi.Response("Bad request (validation errors)"),
#             404: openapi.Response("Session not found")
#         }
#     )
#     def post(self, request):
#         session_id = request.data.get("session_id")
#         user_input = request.data.get("content")
#         chat_type = request.data.get("chat_type")  # Optional

#         if not user_input:
#             return Response({"error": "Message content is required."}, status=400)

#         # Validate or create session
#         if session_id:
#             try:
#                 session_uuid = UUID(session_id)
#                 session = ChatSession.objects.get(session_id=session_uuid, user=request.user)
#             except (ValueError, ChatSession.DoesNotExist):
#                 return Response({"error": "Invalid or unauthorized session ID."}, status=404)
#         else:
#             if not chat_type:
#                 return Response({"error": "chat_type is required for new sessions."}, status=400)

#             if chat_type not in dict(ChatSession.CHAT_TYPE_CHOICES).keys():
#                 return Response({"error": "Invalid chat_type."}, status=400)

#             session = ChatSession.objects.create(user=request.user, chat_type=chat_type)

#         # Save user's message
#         user_msg = ChatMessage.objects.create(
#             session=session,
#             user=request.user,
#             sender="User",
#             content=user_input
#         )

#         # Generate AI response using all previous messages
#         db_messages = session.messages.order_by("timestamp")
#         full_response = ""
#         try:
#             for chunk in stream_gpt_response(user_input, db_messages):
#                 delta = chunk["choices"][0].get("delta", {}).get("content", "")
#                 full_response += delta
#         except Exception as e:
#             return Response({"error": str(e)}, status=500)

#         # Save AI message
#         ai_msg = ChatMessage.objects.create(
#             session=session,
#             user=request.user,
#             sender="AI",
#             content=full_response
#         )

#         return Response({
#             "session": ChatSessionSerializer(session).data,
#             "user_message": ChatMessageSerializer(user_msg).data,
#             "ai_message": ChatMessageSerializer(ai_msg).data,
#             "all_messages": ChatMessageSerializer(session.messages.order_by("timestamp"), many=True).data
#         })
#     def get(self, request):
#         session_id = request.GET.get("session_id")
#         if not session_id:
#             return Response({"error": "session_id is required"}, status=400)

#         try:
#             session_uuid = UUID(session_id)
#             session = ChatSession.objects.get(session_id=session_uuid, user=request.user)
#         except (ValueError, ChatSession.DoesNotExist):
#             return Response({"error": "Invalid or unauthorized session ID."}, status=404)

#         messages = ChatMessageSerializer(session.messages.order_by("timestamp"), many=True).data
#         return Response({
#             "session": ChatSessionSerializer(session).data,
#             "messages": messages
#         })

class UserSessionsAPIView(APIView):
    permission_classes = [IsChatAccessAllowed]

    @swagger_auto_schema(
        operation_summary="Get user's chat sessions",
        operation_description="Get all active chat sessions for the logged-in user.",
        responses={
            200: openapi.Response("User sessions retrieved successfully"),
        }
    )
    def get(self, request):
        """
        Get all active sessions for a user
        """
        user_sessions = ChatSession.get_user_sessions(request.user)
        
        return Response({
            "user_sessions": user_sessions
        })

    @swagger_auto_schema(
        operation_summary="Get or create a chat session",
        operation_description="Get existing session or create new one.",
        responses={
            200: openapi.Response("Session retrieved or created successfully")
        }
    )
    def post(self, request):
        """
        Get or create a chat session
        """
        session, created = ChatSession.get_or_create_session(request.user)
        
        return Response({
            "session": ChatSessionSerializer(session).data,
            "created": created,
            "message": "New session created" if created else "Existing session retrieved"
        })


class ChatStreamAPIView(APIView):
    permission_classes = [IsChatAccessAllowed]

    session_histories = {}  # Session-wise Benji AI history

    @swagger_auto_schema(
        operation_summary="Send a new message",
        operation_description="Send a message and receive an AI response with all session messages.",
        request_body=ChatMessageSerializer,
        responses={
            200: openapi.Response("Message processed successfully"),
            400: openapi.Response("Bad request (validation errors)"),
            404: openapi.Response("Session not found")
        }
    )
    def post(self, request):
        session_id = request.data.get("session_id")
        user_input = request.data.get("content")

        if not user_input:
            return Response({"error": "Message content is required."}, status=400)

        # Validate or create session using new method
        if session_id:
            try:
                session_uuid = UUID(session_id)
                session = ChatSession.objects.get(session_id=session_uuid, user=request.user, is_active=True)
                # Update last activity
                session.updated_at = now()
                session.save()
            except (ValueError, ChatSession.DoesNotExist):
                return Response({"error": "Invalid or unauthorized session ID."}, status=404)
        else:
            # Use new session management method - no chat_type needed
            session, created = ChatSession.get_or_create_session(request.user)

        # Save user's message
        user_msg = ChatMessage.objects.create(
            session=session,
            user=request.user,
            sender="User",
            content=user_input
        )

        full_response = ""
        pdf_url = None

        try:
            from django.core.files.storage import default_storage
            from django.conf import settings
            # Create user-specific local folder for uploaded documents using Django's storage system
            user_folder_name = f"user_{request.user.user_id}"
            relative_upload_path = os.path.join('chat_uploads', user_folder_name)
            user_upload_path = os.path.join(settings.MEDIA_ROOT, relative_upload_path)

            # Get user's claim information (you can get this from user profile or insurance claims)
            try:
                from userdashboard.models import InsuranceClaim
                latest_claim = InsuranceClaim.objects.filter(user=request.user).order_by('-id').first()
                if latest_claim:
                    claim_no = latest_claim.id
                else:
                    claim_no = request.user.user_id
            except:
                claim_no = request.user.user_id

            from .chatbootAi import run_benji_chat

            if str(session.session_id) not in self.session_histories:
                self.session_histories[str(session.session_id)] = []

            # Get the most recent upload_id for this user (if any)
            try:
                latest_upload = UserClaimUpload.objects.filter(
                    user=request.user,
                    is_active=True
                ).order_by('-updated_at').first()
                upload_id = str(latest_upload.upload_id) if latest_upload else None
                # Get PDF URL using Django's storage system
                if latest_upload and hasattr(latest_upload, 'pdf_file') and latest_upload.pdf_file:
                    pdf_url = latest_upload.pdf_file.url
            except Exception:
                upload_id = None
                pdf_url = None

            response_text, updated_history = run_benji_chat(
                user=request.user,
                user_question=user_input,
                chat_history_list=self.session_histories[str(session.session_id)],
                upload_id=upload_id
            )

            self.session_histories[str(session.session_id)] = updated_history
            full_response = response_text

        except Exception as e:
            return Response({"error": f"Chat processing error: {str(e)}"}, status=500)

        ai_msg = ChatMessage.objects.create(
            session=session,
            user=request.user,
            sender="AI",
            content=full_response
        )

        response_data = {
            "session": ChatSessionSerializer(session).data,
            "user_message": ChatMessageSerializer(user_msg).data,
            "ai_message": ChatMessageSerializer(ai_msg).data,
            "all_messages": ChatMessageSerializer(session.messages.order_by("timestamp"), many=True).data
        }
        if pdf_url:
            response_data["pdf_url"] = pdf_url

        return Response(response_data)

    def get(self, request):
        session_id = request.GET.get("session_id")
        if not session_id:
            return Response({"error": "session_id is required"}, status=400)

        try:
            session_uuid = UUID(session_id)
            session = ChatSession.objects.get(session_id=session_uuid, user=request.user, is_active=True)
            # Update last activity when accessing session
            session.updated_at = now()
            session.save()
        except (ValueError, ChatSession.DoesNotExist):
            return Response({"error": "Invalid or unauthorized session ID."}, status=404)

        messages = ChatMessageSerializer(session.messages.order_by("timestamp"), many=True).data
        return Response({
            "session": ChatSessionSerializer(session).data,
            "messages": messages
        })

# views.py

class FlagMessageAPIView(APIView):
    permission_classes = [IsChatAccessAllowed]
    @swagger_auto_schema(
        operation_summary="Save SMS ",
        operation_description="Signup using full name, email, mobile, and password.",
        request_body=FlaggedMessageSerializer,
        responses={
            201: openapi.Response("SMS SAVE SUCCFULLY "),
            400: openapi.Response("Bad request (validation errors)")
        }
    )

    def post(self, request):
        message_id = request.data.get("message_id")
        session_id = request.data.get("session_id")
        flag_type = request.data.get("flag_type")  # Optional

        if not message_id or not session_id:
            return Response(
                {"error": "Both message_id and session_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            message = ChatMessage.objects.select_related("session").get(
                id=message_id,
                session__session_id=session_id,
                user=request.user
            )
        except ChatMessage.DoesNotExist:
            return Response(
                {"error": "Message not found in this session."},
                status=status.HTTP_404_NOT_FOUND
            )

        message.flagged = True
        message.flag_type = flag_type
        message.save()

        flagged_entry, created = FlaggedMessage.objects.get_or_create(
            message=message,
            defaults={"flagged_by": request.user, "flag_type": flag_type}
        )

        # Update flag_type if the entry already existed and a new type is provided
        if not created and flag_type:
            flagged_entry.flag_type = flag_type
            flagged_entry.save()

        return Response({
            "message": "Message flagged successfully.",
            "data": FlaggedMessageSerializer(flagged_entry).data
        }, status=status.HTTP_200_OK)


class FlaggedMessagesListAPIView(APIView):
    permission_classes = [IsChatAccessAllowed]

    def get(self, request):
        flagged_records = FlaggedMessage.objects.filter(
            flagged_by=request.user
        ).select_related("message").order_by("-flagged_at")

        serializer = FlaggedMessageSerializer(flagged_records, many=True)

        return Response({
            "message": "Flagged messages fetched successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



class DownloadChatPDFAPIView(APIView):
    permission_classes = [IsChatAccessAllowed]

    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(session_id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return HttpResponse("Session not found.", status=404)

        messages = session.messages.filter(sender__in=["User", "AI"]).order_by("timestamp")

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="chat_conversation_{session_id}.pdf"'

        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Define colors for modern chat design
        user_color = HexColor("#00A86B")  # Green color
        ai_color = HexColor("#E5E5EA")    # Light gray
        user_text_color = white
        ai_text_color = black
        bg_color = HexColor("#F8F9FA")    # Very light gray background
        header_color = HexColor("#2c3e50")
        
        # Define margins
        left_margin = 40
        right_margin = width - 40
        top_margin = height - 40
        bottom_margin = 40
        
        y = top_margin

        def add_header():
            nonlocal y
            # Header background - reduced height
            p.setFillColor(header_color)
            p.rect(0, y - 25, width, 40, fill=1)
            
            # Chat title - smaller and more compact
            p.setFillColor(white)
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(width/2, y - 8, "💬 Chat Conversation")
            
            # Subtitle - smaller
            p.setFont("Helvetica", 10)
            p.drawCentredString(width/2, y - 20, "Chat Conversation Export")
            
            y -= 40  # Reduced header spacing from 50 to 40

        def draw_user_message(content):
            nonlocal y
            # Split content into lines
            lines = wrap_text(content, max_width=280, font="Helvetica", size=11)
            
            # Calculate bubble dimensions consistently
            if lines:
                max_line_width = max([p.stringWidth(line, "Helvetica", 11) for line in lines if line.strip()])
            else:
                max_line_width = 50
            
            bubble_width = min(max_line_width + 18, 300)  # Reduced padding from 20 to 18
            bubble_height = len(lines) * 14 + 18  # Reduced line spacing and padding
            
            # Position bubble on the right side
            bubble_x = right_margin - bubble_width - 45
            icon_x = right_margin - 20
            icon_y = y - 15
            
            # Check if we need to split the message across pages
            if y - bubble_height < bottom_margin + 30:
                # Calculate how many lines can fit on current page
                available_space = y - bottom_margin - 50  # Space for footer
                lines_that_fit = max(1, int((available_space - 18) / 14))  # At least 1 line
                
                if lines_that_fit < len(lines):
                    # Split the message
                    first_part_lines = lines[:lines_that_fit]
                    remaining_lines = lines[lines_that_fit:]
                    
                    # Draw first part on current page
                    first_bubble_height = len(first_part_lines) * 14 + 18
                    bubble_y = y - first_bubble_height
                    
                    # Draw user icon on the right side
                    p.setFillColor(user_color)
                    p.circle(icon_x, icon_y, 12, fill=1)
                    p.setFillColor(white)
                    p.setFont("Helvetica-Bold", 10)
                    p.drawCentredString(icon_x, icon_y - 3, "U")
                    
                    # Draw first part bubble
                    p.setFillColor(HexColor("#0056A3"))
                    p.roundRect(bubble_x + 2, bubble_y - 2, bubble_width, first_bubble_height, 15, fill=1)
                    p.setFillColor(user_color)
                    p.roundRect(bubble_x, bubble_y, bubble_width, first_bubble_height, 15, fill=1)
                    p.setStrokeColor(HexColor("#4A90E2"))
                    p.setLineWidth(1)
                    p.roundRect(bubble_x, bubble_y, bubble_width, first_bubble_height, 15, fill=0, stroke=1)
                    
                    # Draw first part text
                    p.setFillColor(user_text_color)
                    p.setFont("Helvetica", 11)
                    text_y = bubble_y + first_bubble_height - 16
                    
                    for line in first_part_lines:
                        if line.strip() and text_y > bubble_y + 4:
                            p.drawString(bubble_x + 10, text_y, line)
                        text_y -= 14
                    
                    # Start new page for remaining content
                    add_footer()
                    p.showPage()
                    y = top_margin
                    
                    # Draw remaining part
                    remaining_bubble_height = len(remaining_lines) * 14 + 18
                    bubble_y = y - remaining_bubble_height
                    icon_y = y - 15
                    
                    # Draw user icon on new page
                    p.setFillColor(user_color)
                    p.circle(icon_x, icon_y, 12, fill=1)
                    p.setFillColor(white)
                    p.setFont("Helvetica-Bold", 10)
                    p.drawCentredString(icon_x, icon_y - 3, "U")
                    
                    # Draw remaining part bubble
                    p.setFillColor(HexColor("#0056A3"))
                    p.roundRect(bubble_x + 2, bubble_y - 2, bubble_width, remaining_bubble_height, 15, fill=1)
                    p.setFillColor(user_color)
                    p.roundRect(bubble_x, bubble_y, bubble_width, remaining_bubble_height, 15, fill=1)
                    p.setStrokeColor(HexColor("#4A90E2"))
                    p.setLineWidth(1)
                    p.roundRect(bubble_x, bubble_y, bubble_width, remaining_bubble_height, 15, fill=0, stroke=1)
                    
                    # Draw remaining text
                    p.setFillColor(user_text_color)
                    p.setFont("Helvetica", 11)
                    text_y = bubble_y + remaining_bubble_height - 16
                    
                    for line in remaining_lines:
                        if line.strip() and text_y > bubble_y + 4:
                            p.drawString(bubble_x + 10, text_y, line)
                        text_y -= 14
                    
                    y = bubble_y - 6
                    return
            
            # Normal case - entire message fits on current page
            bubble_y = y - bubble_height
            
            # Draw user icon on the right side
            p.setFillColor(user_color)
            p.circle(icon_x, icon_y, 12, fill=1)
            p.setFillColor(white)
            p.setFont("Helvetica-Bold", 10)
            p.drawCentredString(icon_x, icon_y - 3, "U")
            
            # Draw enhanced user bubble with shadow
            p.setFillColor(HexColor("#0056A3"))
            p.roundRect(bubble_x + 2, bubble_y - 2, bubble_width, bubble_height, 15, fill=1)
            
            # Main bubble
            p.setFillColor(user_color)
            p.roundRect(bubble_x, bubble_y, bubble_width, bubble_height, 15, fill=1)
            
            # Add subtle border highlight
            p.setStrokeColor(HexColor("#4A90E2"))
            p.setLineWidth(1)
            p.roundRect(bubble_x, bubble_y, bubble_width, bubble_height, 15, fill=0, stroke=1)
            
            # Draw message text with consistent positioning
            p.setFillColor(user_text_color)
            p.setFont("Helvetica", 11)
            text_y = bubble_y + bubble_height - 16  # Reduced from 18 to 16
            
            for line in lines:
                if line.strip() and text_y > bubble_y + 4:  # Reduced from 5 to 4
                    p.drawString(bubble_x + 10, text_y, line)
                text_y -= 14  # Reduced from 15 to 14
            
            # Update y position with consistent spacing
            y = bubble_y - 6  # Reduced to 6px spacing after each message

        def draw_ai_message(content):
            nonlocal y
            # Split content into lines with better formatting
            lines = wrap_text(content, max_width=350, font="Helvetica", size=11)
            
            # Calculate bubble dimensions consistently - account for empty lines
            non_empty_lines = [line for line in lines if line.strip()]
            if non_empty_lines:
                max_line_width = max([p.stringWidth(line, "Helvetica", 11) for line in non_empty_lines])
            else:
                max_line_width = 100
            
            bubble_width = min(max_line_width + 18, 370)  # Reduced padding from 20 to 18
            bubble_height = len(lines) * 14 + 18  # Reduced line spacing and padding
            
            # Position bubble on the left side
            bubble_x = left_margin + 45
            icon_x = left_margin + 20
            icon_y = y - 15
            
            # Check if we need to split the message across pages
            if y - bubble_height < bottom_margin + 30:
                # Calculate how many lines can fit on current page
                available_space = y - bottom_margin - 50  # Space for footer
                lines_that_fit = max(1, int((available_space - 18) / 14))  # At least 1 line
                
                if lines_that_fit < len(lines):
                    # Split the message
                    first_part_lines = lines[:lines_that_fit]
                    remaining_lines = lines[lines_that_fit:]
                    
                    # Draw first part on current page
                    first_bubble_height = len(first_part_lines) * 14 + 18
                    bubble_y = y - first_bubble_height
                    
                    # Draw AI icon on the left side
                    p.setFillColor(HexColor("#34495e"))
                    p.circle(icon_x, icon_y, 12, fill=1)
                    p.setFillColor(white)
                    p.setFont("Helvetica-Bold", 9)
                    p.drawCentredString(icon_x, icon_y - 2, "AI")
                    
                    # Draw first part bubble
                    p.setFillColor(HexColor("#D5D8DC"))
                    p.roundRect(bubble_x + 2, bubble_y - 2, bubble_width, first_bubble_height, 15, fill=1)
                    p.setFillColor(ai_color)
                    p.roundRect(bubble_x, bubble_y, bubble_width, first_bubble_height, 15, fill=1)
                    p.setStrokeColor(HexColor("#BDC3C7"))
                    p.setLineWidth(1)
                    p.roundRect(bubble_x, bubble_y, bubble_width, first_bubble_height, 15, fill=0, stroke=1)
                    
                    # Draw first part text
                    p.setFillColor(ai_text_color)
                    p.setFont("Helvetica", 11)
                    text_y = bubble_y + first_bubble_height - 16
                    
                    for line in first_part_lines:
                        if line.strip() and text_y > bubble_y + 4:
                            # Handle bold formatting
                            if "**" in line:
                                parts = line.split("**")
                                current_x = bubble_x + 10
                                for i, part in enumerate(parts):
                                    if part:
                                        if i % 2 == 1:
                                            p.setFont("Helvetica-Bold", 11)
                                        else:
                                            p.setFont("Helvetica", 11)
                                        p.drawString(current_x, text_y, part)
                                        current_x += p.stringWidth(part, p._fontname, 11)
                            else:
                                p.setFont("Helvetica", 11)
                                p.drawString(bubble_x + 10, text_y, line)
                        text_y -= 14
                    
                    # Start new page for remaining content
                    add_footer()
                    p.showPage()
                    y = top_margin
                    
                    # Draw remaining part
                    remaining_bubble_height = len(remaining_lines) * 14 + 18
                    bubble_y = y - remaining_bubble_height
                    icon_y = y - 15
                    
                    # Draw AI icon on new page
                    p.setFillColor(HexColor("#34495e"))
                    p.circle(icon_x, icon_y, 12, fill=1)
                    p.setFillColor(white)
                    p.setFont("Helvetica-Bold", 9)
                    p.drawCentredString(icon_x, icon_y - 2, "AI")
                    
                    # Draw remaining part bubble
                    p.setFillColor(HexColor("#D5D8DC"))
                    p.roundRect(bubble_x + 2, bubble_y - 2, bubble_width, remaining_bubble_height, 15, fill=1)
                    p.setFillColor(ai_color)
                    p.roundRect(bubble_x, bubble_y, bubble_width, remaining_bubble_height, 15, fill=1)
                    p.setStrokeColor(HexColor("#BDC3C7"))
                    p.setLineWidth(1)
                    p.roundRect(bubble_x, bubble_y, bubble_width, remaining_bubble_height, 15, fill=0, stroke=1)
                    
                    # Draw remaining text
                    p.setFillColor(ai_text_color)
                    p.setFont("Helvetica", 11)
                    text_y = bubble_y + remaining_bubble_height - 16
                    
                    for line in remaining_lines:
                        if line.strip() and text_y > bubble_y + 4:
                            # Handle bold formatting
                            if "**" in line:
                                parts = line.split("**")
                                current_x = bubble_x + 10
                                for i, part in enumerate(parts):
                                    if part:
                                        if i % 2 == 1:
                                            p.setFont("Helvetica-Bold", 11)
                                        else:
                                            p.setFont("Helvetica", 11)
                                        p.drawString(current_x, text_y, part)
                                        current_x += p.stringWidth(part, p._fontname, 11)
                            else:
                                p.setFont("Helvetica", 11)
                                p.drawString(bubble_x + 10, text_y, line)
                        text_y -= 14
                    
                    y = bubble_y - 6
                    return
            
            # Normal case - entire message fits on current page
            bubble_y = y - bubble_height
            
            # Draw AI icon on the left side
            p.setFillColor(HexColor("#34495e"))
            p.circle(icon_x, icon_y, 12, fill=1)
            p.setFillColor(white)
            p.setFont("Helvetica-Bold", 9)
            p.drawCentredString(icon_x, icon_y - 2, "AI")
            
            # Draw enhanced AI bubble with shadow
            p.setFillColor(HexColor("#D5D8DC"))
            p.roundRect(bubble_x + 2, bubble_y - 2, bubble_width, bubble_height, 15, fill=1)
            
            # Main bubble
            p.setFillColor(ai_color)
            p.roundRect(bubble_x, bubble_y, bubble_width, bubble_height, 15, fill=1)
            
            # Add subtle border
            p.setStrokeColor(HexColor("#BDC3C7"))
            p.setLineWidth(1)
            p.roundRect(bubble_x, bubble_y, bubble_width, bubble_height, 15, fill=0, stroke=1)
            
            # Draw message text within the bubble with consistent positioning
            p.setFillColor(ai_text_color)
            p.setFont("Helvetica", 11)
            text_y = bubble_y + bubble_height - 16  # Reduced from 18 to 16
            
            for line in lines:
                if line.strip() and text_y > bubble_y + 4:  # Reduced from 5 to 4
                    # Check for bold formatting (simple **text** detection)
                    if "**" in line:
                        # Handle bold text (simplified)
                        parts = line.split("**")
                        current_x = bubble_x + 10
                        for i, part in enumerate(parts):
                            if part:  # Skip empty parts
                                if i % 2 == 1:  # Odd index = bold
                                    p.setFont("Helvetica-Bold", 11)
                                else:  # Even index = normal
                                    p.setFont("Helvetica", 11)
                                p.drawString(current_x, text_y, part)
                                current_x += p.stringWidth(part, p._fontname, 11)
                    else:
                        p.setFont("Helvetica", 11)
                        p.drawString(bubble_x + 10, text_y, line)
                text_y -= 14  # Reduced from 15 to 14
            
            # Update y position with consistent spacing
            y = bubble_y - 6  # Reduced to 6px spacing after each message

        def wrap_text(text, max_width, font, size):
            """Wrap text to fit within specified width with proper formatting"""
            import re
            
            # First, handle special formatting patterns
            text = text.replace('. -', '.\n-')  # Line break before bullet points
            text = text.replace(': -', ':\n-')  # Line break before bullet points after colons
            
            # Handle numbered lists
            text = re.sub(r'(\d+\.\s\*\*)', r'\n\1', text)  # Line break before numbered items
            text = re.sub(r'(\*\*[^*]+\*\*:)', r'\1\n', text)  # Line break after bold headers
            
            # Split by explicit line breaks first
            paragraphs = text.split('\n')
            lines = []
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    lines.append('')  # Keep empty lines for spacing
                    continue
                    
                words = paragraph.split()
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    if p.stringWidth(test_line, font, size) <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
            
            # Remove excessive empty lines to prevent spacing issues
            cleaned_lines = []
            empty_count = 0
            for line in lines:
                if not line.strip():
                    empty_count += 1
                    if empty_count <= 1:  # Allow max 1 empty line
                        cleaned_lines.append(line)
                else:
                    empty_count = 0
                    cleaned_lines.append(line)
            
            return cleaned_lines

        def add_footer():
            nonlocal y
            # Minimal footer space
            y = bottom_margin + 20
            
            # Footer background - reduced height
            p.setFillColor(HexColor("#ecf0f1"))
            p.rect(0, 0, width, bottom_margin + 15, fill=1)
            
            # Footer content - smaller and more compact
            p.setFillColor(HexColor("#7f8c8d"))
            p.setFont("Helvetica", 8)
            p.drawString(left_margin, bottom_margin - 5, "Generated by AI Chat System")
            
            from datetime import datetime
            current_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
            p.drawRightString(right_margin, bottom_margin - 5, f"Exported: {current_date}")
            
            # Add page number
            page_num = p.getPageNumber()
            p.setFillColor(HexColor("#7f8c8d"))
            p.setFont("Helvetica", 8)
            p.drawCentredString(width/2, bottom_margin - 5, f"Page {page_num}")
            
            # Minimal decorative elements
            p.setFillColor(HexColor("#bdc3c7"))
            p.setFont("Helvetica", 7)
            p.drawCentredString(width/2, 10, "💬 Secure & Confidential Chat Export")

        # Start building the PDF
        add_header()

        # Add messages with consistent spacing
        for i, msg in enumerate(messages):
            if msg.sender == "User":
                draw_user_message(msg.content)
            else:  # AI message
                draw_ai_message(msg.content)

        # Add end of conversation indicator with consistent spacing
        y -= 8  # Reduced spacing before end indicator
        if y < bottom_margin + 40:  # Reduced check margin
            add_footer()
            p.showPage()
            y = top_margin - 8
        
        p.setFillColor(HexColor("#95a5a6"))
        p.roundRect(left_margin + 100, y - 18, width - 200, 22, 6, fill=1)  # Smaller indicator
        p.setFillColor(white)
        p.setFont("Helvetica-Bold", 8)  # Smaller font
        p.drawCentredString(width/2, y - 10, "✨ End of Conversation")

        add_footer()
        
        p.save()
        return response


def split_text(text, max_chars):
    """
    Splits text into lines with at most max_chars characters.
    """
    words = text.split()
    lines = []
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > max_chars:
            lines.append(line)
            line = word
        else:
            line += (" " if line else "") + word
    if line:
        lines.append(line)
    return lines


# # class ClaimAnalysisAPIView(APIView):
# #     def post(self, request, *args, **kwargs):
# #         serializer = ClaimAnalysisSerializer(data=request.data)
# #         if serializer.is_valid():
# #             data = serializer.validated_data
            
# #             # Save uploaded files to temporary files
# #             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as policy_file, \
# #                  tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as receipt_file:
                
# #                 policy_file.write(data['policy'].read())
# #                 receipt_file.write(data['receipt'].read())
# #                 policy_path = policy_file.name
# #                 receipt_path = receipt_file.name

# #             try:
# #                 # Call your AI function
# #                 result = main(
# #                     claim_no=data["claim_no"],
# #                     list_item=data["list_item"],
# #                     name=data["name"],
# #                     phone=data["phone"],
# #                     email=data["email"],
# #                     pdf1=policy_path,
# #                     pdf2=receipt_path
# #                 )
# #             finally:
# #                 # Cleanup temporary files
# #                 os.remove(policy_path)
# #                 os.remove(receipt_path)

# #             return Response({"analysis": result}, status=status.HTTP_200_OK)

# #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class ClaimAnalysisAPIView(APIView):
#     permission_classes = [IsChatAccessAllowed]
#     def post(self, request, *args, **kwargs):
#         serializer = ClaimAnalysisSerializer(data=request.data)
#         if serializer.is_valid():
#             data = serializer.validated_data

#             # Save uploaded files to temporary files
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as policy_file, \
#                  tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as receipt_file:

#                 policy_file.write(data['policy'].read())
#                 receipt_file.write(data['receipt'].read())
#                 policy_path = policy_file.name
#                 receipt_path = receipt_file.name

#             try:
#                 # Call your AI function to get the result
#                 result = main(
#                     claim_no=data["claim_no"],
#                     list_item=data["list_item"],
#                     name=data["name"],
#                     phone=data["phone"],
#                     email=data["email"],
#                     pdf1=policy_path,
#                     pdf2=receipt_path
#                 )
#             finally:
#                 os.remove(policy_path)
#                 os.remove(receipt_path)

#             # Create PDF content with professional formatting
#             buffer = BytesIO()
#             p = canvas.Canvas(buffer, pagesize=letter)
#             width, height = letter

#             # Define colors
#             header_color = HexColor("#2c3e50")
#             section_color = HexColor("#34495e")
#             accent_color = HexColor("#3498db")
#             text_color = HexColor("#2c3e50")
#             bg_color = HexColor("#ecf0f1")

#             # Define margins and spacing
#             left_margin = 50
#             right_margin = width - 50
#             top_margin = height - 50
#             bottom_margin = 50
#             max_width = right_margin - left_margin
            
#             y = top_margin

#             def add_header():
#                 nonlocal y
#                 # Add header background
#                 p.setFillColor(header_color)
#                 p.rect(0, y - 20, width, 60, fill=1)
                
#                 # Add company logo/title
#                 p.setFillColor(white)
#                 p.setFont("Helvetica-Bold", 24)
#                 p.drawCentredString(width/2, y + 10, "INSURANCE CLAIM ANALYSIS REPORT")
                
#                 # Add date
#                 p.setFont("Helvetica", 12)
#                 from datetime import datetime
#                 current_date = datetime.now().strftime("%B %d, %Y")
#                 p.drawRightString(right_margin - 10, y - 5, f"Generated: {current_date}")
                
#                 y -= 80

#             def add_section_header(title, add_space_before=True):
#                 nonlocal y
#                 if add_space_before:
#                     y -= 20  # Space before section
                
#                 # Check if we need a new page
#                 if y < bottom_margin + 100:
#                     p.showPage()
#                     y = top_margin
                
#                 # Section header background
#                 p.setFillColor(section_color)
#                 p.rect(left_margin - 10, y - 5, max_width + 20, 25, fill=1)
                
#                 # Section title
#                 p.setFillColor(white)
#                 p.setFont("Helvetica-Bold", 14)
#                 p.drawString(left_margin, y + 5, title)
                
#                 y -= 35

#             def add_subsection_header(title):
#                 nonlocal y
#                 y -= 10  # Space before subsection
                
#                 # Check if we need a new page
#                 if y < bottom_margin + 50:
#                     p.showPage()
#                     y = top_margin
                
#                 p.setFillColor(accent_color)
#                 p.setFont("Helvetica-Bold", 12)
#                 p.drawString(left_margin, y, title)
#                 y -= 20

#             def add_text(text, font="Helvetica", size=11, indent=0, bullet=False):
#                 nonlocal y
#                 p.setFillColor(text_color)
#                 p.setFont(font, size)
                
#                 # Add bullet if requested
#                 bullet_offset = 0
#                 if bullet:
#                     p.drawString(left_margin + indent, y, "•")
#                     bullet_offset = 15
                
#                 # Split text into lines that fit within the max width
#                 words = text.split(' ')
#                 lines = []
#                 line = []
#                 available_width = max_width - indent - bullet_offset

#                 for word in words:
#                     test_line = ' '.join(line + [word])
#                     if p.stringWidth(test_line, font, size) <= available_width:
#                         line.append(word)
#                     else:
#                         if line:
#                             lines.append(' '.join(line))
#                         line = [word]
                
#                 if line:
#                     lines.append(' '.join(line))

#                 # Draw each line
#                 for i, line in enumerate(lines):
#                     # Check if we need a new page
#                     if y < bottom_margin + 20:
#                         p.showPage()
#                         y = top_margin
#                         p.setFont(font, size)
#                         p.setFillColor(text_color)
                    
#                     # For continuation lines, add extra indent
#                     line_indent = indent + bullet_offset if i == 0 or not bullet else indent + bullet_offset + 10
#                     p.drawString(left_margin + line_indent, y, line)
#                     y -= 16

#                 y -= 5  # Extra space after paragraph

#             def add_key_value_pair(key, value, indent=20):
#                 nonlocal y
#                 # Check if we need a new page
#                 if y < bottom_margin + 20:
#                     p.showPage()
#                     y = top_margin
                
#                 p.setFillColor(text_color)
#                 p.setFont("Helvetica-Bold", 11)
#                 p.drawString(left_margin + indent, y, f"{key}:")
                
#                 p.setFont("Helvetica", 11)
#                 key_width = p.stringWidth(f"{key}:", "Helvetica-Bold", 11)
#                 p.drawString(left_margin + indent + key_width + 10, y, str(value))
#                 y -= 18

#             def add_divider():
#                 nonlocal y
#                 y -= 10
#                 p.setStrokeColor(bg_color)
#                 p.setLineWidth(1)
#                 p.line(left_margin, y, right_margin, y)
#                 y -= 15

#             # Start building the PDF
#             add_header()

#             # Executive Summary Section
#             add_section_header("EXECUTIVE SUMMARY", add_space_before=False)
#             add_text("This comprehensive report provides a detailed analysis of the insurance claim submitted. "
#                     "Our assessment includes verification of claim details, item-by-item evaluation, financial breakdown, "
#                     "policy compliance review, and strategic recommendations. All numerical data, dates, and specific "
#                     "details have been meticulously preserved to ensure precise evaluation and informed decision-making.")

#             # Claim Details Section
#             add_section_header("CLAIM DETAILS VERIFICATION")
#             add_key_value_pair("Claim Number", data['claim_no'])
#             add_key_value_pair("Claimant Name", data['name'])
#             add_key_value_pair("Contact Phone", data['phone'])
#             add_key_value_pair("Contact Email", data['email'])
#             add_key_value_pair("Claimed Items", data['list_item'])

#             add_divider()

#             # Item Analysis Section
#             add_section_header("ITEM-BY-ITEM ANALYSIS")
            
#             add_subsection_header("Claimed Items Overview")
#             add_text(f"Items under review: {data['list_item']}", indent=20)
            
#             add_subsection_header("Policy Coverage Assessment")
#             add_text("The policy document requires detailed examination to determine specific coverage parameters for the claimed items. "
#                     "Initial review indicates that explicit coverage terms for the specified items need further investigation.", indent=20)
            
#             add_subsection_header("Receipts Verification")
#             add_text("Receipt documentation analysis reveals discrepancies between claimed items and provided proof of purchase. "
#                     "The submitted receipts detail transactions that do not directly correlate with the items specified in this claim.", indent=20)

#             # Financial Breakdown Section
#             add_section_header("FINANCIAL BREAKDOWN")
            
#             add_text("Financial Assessment Summary:", font="Helvetica-Bold", size=12)
#             add_text("• Total Claim Amount: Pending verification due to insufficient item-specific pricing documentation", bullet=True, indent=20)
#             add_text("• Receipt Total: $1,000 (transaction category: Land purchase)", bullet=True, indent=20)
#             add_text("• Covered Amounts: To be determined following policy specification review", bullet=True, indent=20)
#             add_text("• Deductibles: Not specified in current documentation", bullet=True, indent=20)
#             add_text("• Estimated Out-of-Pocket: Cannot be calculated without complete pricing information", bullet=True, indent=20)

#             # Policy Compliance Section
#             add_section_header("POLICY COMPLIANCE ASSESSMENT")
            
#             add_subsection_header("Coverage Analysis")
#             add_text("The policy documentation outlines general financial objectives and strategic frameworks but lacks "
#                     "specific details regarding coverage for the items in question.", indent=20)
            
#             add_subsection_header("Documentation Compliance")
#             add_text("Current submission exhibits gaps between claimed items and supporting documentation, "
#                     "indicating potential compliance issues that require immediate attention.", indent=20)

#             # Recommendations Section
#             add_section_header("FINAL RECOMMENDATIONS")
            
#             add_subsection_header("Decision Status")
#             add_text("RECOMMENDATION: CLAIM DENIAL", font="Helvetica-Bold", size=12, indent=20)
            
#             add_subsection_header("Justification")
#             add_text("The claim lacks sufficient documentation establishing a clear connection between claimed items and policy coverage. "
#                     "The provided receipts do not substantiate the specific items listed in this claim.", indent=20)

#             # Next Steps Section
#             add_section_header("REQUIRED NEXT STEPS")
            
#             add_text("To proceed with claim resolution, the following actions are required:", font="Helvetica-Bold")
            
#             add_text("1. Comprehensive Policy Review", font="Helvetica-Bold", bullet=True, indent=20)
#             add_text("Conduct detailed examination of policy terms to identify specific coverage provisions for claimed items.", indent=40)
            
#             add_text("2. Enhanced Documentation Submission", font="Helvetica-Bold", bullet=True, indent=20)
#             add_text("Request supplementary documentation directly linking claimed items to policy coverage terms.", indent=40)
            
#             add_text("3. Receipt Clarification", font="Helvetica-Bold", bullet=True, indent=20)
#             add_text("Obtain itemized receipts specifically detailing the claimed items to validate the submission.", indent=40)
            
#             add_text("4. Claim Reassessment", font="Helvetica-Bold", bullet=True, indent=20)
#             add_text("Schedule comprehensive review upon receipt of required documentation and policy clarification.", indent=40)

#             # Footer
#             y -= 30
#             if y < bottom_margin + 50:
#                 p.showPage()
#                 y = top_margin - 30
            
#             p.setFillColor(header_color)
#             p.rect(0, bottom_margin - 30, width, 40, fill=1)
            
#             p.setFillColor(white)
#             p.setFont("Helvetica", 10)
#             p.drawCentredString(width/2, bottom_margin - 10, "This report is confidential and intended solely for authorized personnel")
#             p.drawString(left_margin, bottom_margin - 25, "Generated by AI Insurance Analysis System")
#             p.drawRightString(right_margin, bottom_margin - 25, f"Page 1 of 1")

#             # Save the PDF
#             p.save()
#             buffer.seek(0)

#             # Return PDF as a response
#             return FileResponse(buffer, as_attachment=True, filename="claim_analysis_report.pdf")

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileUploadAPIView(APIView):
    permission_classes = [IsChatAccessAllowed]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Upload files and claim details for AI analysis",
        operation_description="Upload PDF, text, or other documents along with detailed claim information to your personal knowledge base. Each user has their own isolated folder. Files and claim details are used by the AI to provide more accurate and personalized responses to your insurance claim questions.",
        manual_parameters=[
            openapi.Parameter(
                'files',
                openapi.IN_FORM,
                description="Files to upload (PDF, TXT, DOC, etc.) - will be saved to your personal knowledge base",
                type=openapi.TYPE_FILE,
                required=False
            ),
            # Claim Setup Assistant Fields (matching the form)
            openapi.Parameter(
                'insurance_company_name',
                openapi.IN_FORM,
                description="Insurance Company Name",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'policy_number',
                openapi.IN_FORM,
                description="Policy Number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'police_report_number',
                openapi.IN_FORM,
                description="Police Report Number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'adjuster_name',
                openapi.IN_FORM,
                description="Adjuster Name",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'adjuster_phone_number',
                openapi.IN_FORM,
                description="Adjuster phone number or Enter phone number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'add_claim_number',
                openapi.IN_FORM,
                description="Add Claim Number - Enter claim number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'adjuster_email',
                openapi.IN_FORM,
                description="Adjuster Email - Enter email address",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: openapi.Response("Files and claim details uploaded to personal knowledge base successfully"),
            400: openapi.Response("Bad request (invalid files or session)")
        }
    )
    def post(self, request):
        files = request.FILES.getlist('files')
        
        # Extract claim information from request (matching the form fields)
        claim_info = {
            'insurance_company_name': request.data.get('insurance_company_name'),
            'policy_number': request.data.get('policy_number'),
            'police_report_number': request.data.get('police_report_number'),
            'adjuster_name': request.data.get('adjuster_name'),
            'adjuster_phone_number': request.data.get('adjuster_phone_number'),
            'add_claim_number': request.data.get('add_claim_number'),
            'adjuster_email': request.data.get('adjuster_email')
        }
        
        # Filter out empty values
        claim_info = {k: v for k, v in claim_info.items() if v and v.strip()}
        
        # Require either files or claim information
        if not files and not claim_info:
            return Response({"error": "No files or claim information provided."}, status=400)
        
        # Get or create the most recent active claim upload for the user
        claim_upload = UserClaimUpload.objects.filter(
            user=request.user, 
            is_active=True
        ).order_by('-updated_at').first()
        
        if not claim_upload:
            # Create new claim upload record
            claim_upload = UserClaimUpload.objects.create(user=request.user)
        
        # Always create or get a session for the user (for compatibility)
        session, created = ChatSession.get_or_create_session(request.user)
        
        # Create user-specific folder structure using claim upload ID
        user_folder_name = f"user_{request.user.user_id}_{str(claim_upload.upload_id)[:8]}"
        user_upload_path = os.path.join('media', 'chat_uploads', user_folder_name)
        
        # Create directory if it doesn't exist
        os.makedirs(user_upload_path, exist_ok=True)
        
        # Update claim upload folder path
        claim_upload.upload_folder_path = user_upload_path
        claim_upload.save()
        
        uploaded_files = []

        # Remove all previous PDFs before saving new ones
        if files:
            for f in os.listdir(user_upload_path):
                if f.lower().endswith('.pdf'):
                    try:
                        os.remove(os.path.join(user_upload_path, f))
                    except Exception as e:
                        print(f"Error deleting old PDF {f}: {e}")

        # Process file uploads if any
        for file in files:
            # Create a unique filename to avoid conflicts
            unique_filename = f"{get_random_string(8)}_{file.name}"
            file_path = os.path.join(user_upload_path, unique_filename)

            # Save file to user's specific folder
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            uploaded_files.append({
                'filename': file.name,
                'saved_as': unique_filename,
                'path': file_path,
                'size': file.size,
                'content_type': file.content_type
            })
        
        # Update files metadata in claim upload record
        if uploaded_files:
            claim_upload.files_metadata = uploaded_files
        
        # Update claim information
        if claim_info:
            claim_upload.update_claim_info(claim_info)
            
            # Save claim information to a JSON file for AI to access
            claim_info_file = os.path.join(user_upload_path, 'claim_information.json')
            with open(claim_info_file, 'w') as f:
                json.dump(claim_info, f, indent=2)
            
            # Create organized folder structure based on claim information
            try:
                from .chatbootAi import create_claim_folder_structure
                organized_folder, folders_created = create_claim_folder_structure(user_upload_path, claim_info)
                if folders_created:
                    print(f"Created organized folder structure: {organized_folder}")
                    # Move uploaded files to the documents folder if organized structure was created
                    if uploaded_files and organized_folder != user_upload_path:
                        docs_folder = os.path.join(organized_folder, 'documents')
                        for file_info in uploaded_files:
                            old_path = file_info['path']
                            new_path = os.path.join(docs_folder, file_info['saved_as'])
                            if os.path.exists(old_path):
                                os.rename(old_path, new_path)
                                file_info['path'] = new_path
                                file_info['organized_location'] = docs_folder
                        # Update metadata in claim upload
                        claim_upload.files_metadata = uploaded_files
            except Exception as e:
                print(f"Error creating organized structure: {e}")
        
        # Save the updated claim upload
        claim_upload.save()
        
        return Response({
            "message": "Files and claim details uploaded successfully to your personal knowledge base",
            "claim_upload": UserClaimUploadSerializer(claim_upload).data,
            "session": ChatSessionSerializer(session).data,
            "user_folder": user_folder_name,
            "upload_path": user_upload_path,
            "uploaded_files": uploaded_files,
            "files_count": len(uploaded_files),
            "claim_information": claim_info,
            "claim_fields_updated": len(claim_info)
        })


class ClaimUploadRetrieveUpdateAPIView(APIView):
    """
    API View to retrieve and update user's claim uploads by ID
    GET: Retrieve claim upload data by upload_id
    PATCH: Update claim upload data by upload_id
    """
    permission_classes = [IsChatAccessAllowed]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Retrieve claim upload by ID",
        operation_description="Retrieve user's claim information and uploaded files by upload_id. This allows access to data across different devices.",
        responses={
            200: openapi.Response("Claim upload data retrieved successfully"),
            404: openapi.Response("Claim upload not found")
        }
    )
    def get(self, request, upload_id):
        try:
            claim_upload = UserClaimUpload.objects.get(
                upload_id=upload_id, 
                user=request.user, 
                is_active=True
            )
        except UserClaimUpload.DoesNotExist:
            return Response({"error": "Claim upload not found."}, status=404)

        return Response({
            "message": "Claim upload retrieved successfully",
            "claim_upload": UserClaimUploadSerializer(claim_upload).data
        })

    @swagger_auto_schema(
        operation_summary="Update claim upload by ID",
        operation_description="Update user's claim information and/or upload new files by upload_id. This allows updating data from any device.",
        manual_parameters=[
            openapi.Parameter(
                'files',
                openapi.IN_FORM,
                description="New files to upload (will replace existing files)",
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'insurance_company_name',
                openapi.IN_FORM,
                description="Insurance Company Name",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'policy_number',
                openapi.IN_FORM,
                description="Policy Number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'police_report_number',
                openapi.IN_FORM,
                description="Police Report Number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'adjuster_name',
                openapi.IN_FORM,
                description="Adjuster Name",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'adjuster_phone_number',
                openapi.IN_FORM,
                description="Adjuster phone number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'add_claim_number',
                openapi.IN_FORM,
                description="Claim Number",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'adjuster_email',
                openapi.IN_FORM,
                description="Adjuster Email",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: openapi.Response("Claim upload updated successfully"),
            404: openapi.Response("Claim upload not found")
        }
    )
    def patch(self, request, upload_id):
        try:
            claim_upload = UserClaimUpload.objects.get(
                upload_id=upload_id, 
                user=request.user, 
                is_active=True
            )
        except UserClaimUpload.DoesNotExist:
            return Response({"error": "Claim upload not found."}, status=404)

        files = request.FILES.getlist('files')
        
        # Extract claim information from request
        claim_info = {
            'insurance_company_name': request.data.get('insurance_company_name'),
            'policy_number': request.data.get('policy_number'),
            'police_report_number': request.data.get('police_report_number'),
            'adjuster_name': request.data.get('adjuster_name'),
            'adjuster_phone_number': request.data.get('adjuster_phone_number'),
            'add_claim_number': request.data.get('add_claim_number'),
            'adjuster_email': request.data.get('adjuster_email')
        }
        
        # Filter out empty values
        claim_info = {k: v for k, v in claim_info.items() if v and v.strip()}
        
        # Require either files or claim information for update
        if not files and not claim_info:
            return Response({"error": "No files or claim information provided for update."}, status=400)

        user_upload_path = claim_upload.upload_folder_path
        if not user_upload_path:
            # Create folder path if it doesn't exist
            user_folder_name = f"user_{request.user.user_id}_{str(claim_upload.upload_id)[:8]}"
            user_upload_path = os.path.join('media', 'chat_uploads', user_folder_name)
            claim_upload.upload_folder_path = user_upload_path

        # Create directory if it doesn't exist
        os.makedirs(user_upload_path, exist_ok=True)
        
        uploaded_files = []

        # Process file uploads if any
        if files:
            # Remove all previous files before saving new ones
            try:
                if os.path.exists(user_upload_path):
                    for f in os.listdir(user_upload_path):
                        if not f.endswith('.json'):  # Keep JSON files
                            try:
                                os.remove(os.path.join(user_upload_path, f))
                            except Exception as e:
                                print(f"Error deleting old file {f}: {e}")
            except Exception as e:
                print(f"Error accessing upload directory: {e}")

            # Save new files
            for file in files:
                unique_filename = f"{get_random_string(8)}_{file.name}"
                file_path = os.path.join(user_upload_path, unique_filename)

                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)

                uploaded_files.append({
                    'filename': file.name,
                    'saved_as': unique_filename,
                    'path': file_path,
                    'size': file.size,
                    'content_type': file.content_type
                })
            
            # Update files metadata
            claim_upload.files_metadata = uploaded_files

        # Update claim information
        if claim_info:
            claim_upload.update_claim_info(claim_info)
            
            # Update JSON file
            claim_info_file = os.path.join(user_upload_path, 'claim_information.json')
            with open(claim_info_file, 'w') as f:
                json.dump(claim_upload.get_claim_info_dict(), f, indent=2)

        # Save updated claim upload
        claim_upload.save()

        return Response({
            "message": "Claim upload updated successfully",
            "claim_upload": UserClaimUploadSerializer(claim_upload).data,
            "updated_files": uploaded_files,
            "files_count": len(uploaded_files) if files else len(claim_upload.files_metadata or []),
            "claim_information": claim_upload.get_claim_info_dict(),
            "claim_fields_updated": len(claim_info)
        })


class UserClaimUploadsListAPIView(APIView):
    """
    API View to list all user's claim uploads
    """
    permission_classes = [IsChatAccessAllowed]

    @swagger_auto_schema(
        operation_summary="List user's claim uploads",
        operation_description="Get all active claim uploads for the logged-in user.",
        responses={
            200: openapi.Response("User claim uploads retrieved successfully"),
        }
    )
    def get(self, request):
        claim_uploads = UserClaimUpload.objects.filter(
            user=request.user, 
            is_active=True
        ).order_by('-updated_at')

        return Response({
            "message": "User claim uploads retrieved successfully",
            "claim_uploads": UserClaimUploadSerializer(claim_uploads, many=True).data,
            "total_uploads": claim_uploads.count()
        })